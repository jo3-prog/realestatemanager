from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsApprovedAgentOrAdmin
from notifications.models import Notification
from notifications.services import notify, send_plain_email

from .models import Inquiry
from .serializers import InquirySerializer, InquiryResponseSerializer


class InquiryViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = InquirySerializer
    filterset_fields = ["status", "property"]
    search_fields = ["name", "email", "message"]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]          # visitors can ask questions without an account
        if self.action == "respond":
            return [IsApprovedAgentOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inquiry.objects.none()
        user = self.request.user
        qs = Inquiry.objects.select_related("property")
        if user.is_admin_role:
            return qs                                         # admin: all
        if user.is_approved_agent:
            return qs.filter(property__created_by=user)       # agent: about MY listings
        return qs.filter(Q(user=user) | Q(email__iexact=user.email))  # user: my own

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        inquiry = serializer.save(user=user)
        agent = inquiry.property.created_by
        notify(agent, "New inquiry received",
               f'{inquiry.name} asked about "{inquiry.property.title}": {inquiry.message}',
               Notification.Type.INQUIRY)

    @extend_schema(request=InquiryResponseSerializer, responses=InquirySerializer)
    @action(detail=True, methods=["patch"])
    def respond(self, request, pk=None):
        """PATCH /api/inquiries/{id}/respond/ : the agent answers the inquiry (email is sent)."""
        inquiry = self.get_object()
        data = InquiryResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        inquiry.response = data.validated_data["response"]
        inquiry.status = Inquiry.Status.RESPONDED
        inquiry.responded_at = timezone.now()
        inquiry.save()
        subject = f'Reply about "{inquiry.property.title}"'
        if inquiry.user:
            notify(inquiry.user, subject, inquiry.response, Notification.Type.INQUIRY)
        else:
            send_plain_email(inquiry.email, subject, inquiry.response)
        return Response(InquirySerializer(inquiry).data)
