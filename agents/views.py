from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from notifications.models import Notification
from notifications.services import notify

from .models import AgentProfile
from .serializers import (
    AgentDecisionSerializer,
    AgentProfileSerializer,
    AgentRegisterSerializer,
)


class AgentRegisterView(generics.CreateAPIView):
    """POST /api/agents/register/ : apply to become an agent (starts as 'pending')."""
    serializer_class = AgentRegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "Application submitted. You can list properties once an admin approves you.",
                "user": {"id": user.id, "email": user.email, "role": user.role},
            },
            status=status.HTTP_201_CREATED,
        )


class AgentPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/agents/ and /api/agents/{id}/ : public list of APPROVED agents."""
    queryset = AgentProfile.objects.filter(status=AgentProfile.Status.APPROVED).select_related("user")
    serializer_class = AgentProfileSerializer
    permission_classes = [AllowAny]
    search_fields = ["company_name", "user__first_name", "user__last_name"]


class AgentMeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/agents/me/ : an agent manages their own profile."""
    serializer_class = AgentProfileSerializer

    def get_object(self):
        profile = getattr(self.request.user, "agent_profile", None)
        if profile is None:
            raise PermissionDenied("You do not have an agent profile.")
        return profile


class AdminAgentListView(generics.ListAPIView):
    """GET /api/admin/agents/ (?status=pending|approved|rejected)"""
    queryset = AgentProfile.objects.select_related("user")
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ["status"]


class PendingAgentListView(AdminAgentListView):
    """GET /api/admin/agents/pending/ : agents waiting for a decision."""
    queryset = AgentProfile.objects.filter(status=AgentProfile.Status.PENDING).select_related("user")


class _AgentDecisionView(generics.GenericAPIView):
    """Shared logic for approve / reject."""
    queryset = AgentProfile.objects.select_related("user")
    permission_classes = [IsAdminRole]
    serializer_class = AgentDecisionSerializer

    new_status = None

    @extend_schema(responses=AgentProfileSerializer)
    def patch(self, request, pk):
        profile = self.get_object()
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        profile.status = self.new_status
        profile.reviewed_at = timezone.now()
        profile.rejection_reason = data.validated_data.get("reason", "") if self.new_status == "rejected" else ""
        profile.save()
        self.send_email(profile)
        return Response(AgentProfileSerializer(profile).data)

    def send_email(self, profile):
        raise NotImplementedError


class ApproveAgentView(_AgentDecisionView):
    """PATCH /api/admin/agents/{id}/approve/"""
    new_status = AgentProfile.Status.APPROVED

    def send_email(self, profile):
        notify(profile.user, "Your agent account was approved",
               "Congratulations! You can now create property listings.",
               Notification.Type.AGENT)


class RejectAgentView(_AgentDecisionView):
    """PATCH /api/admin/agents/{id}/reject/  (optional body: {"reason": "..."})"""
    new_status = AgentProfile.Status.REJECTED

    def send_email(self, profile):
        notify(profile.user, "Your agent application was rejected",
               f"Sorry, your application was not approved. {profile.rejection_reason}",
               Notification.Type.AGENT)
