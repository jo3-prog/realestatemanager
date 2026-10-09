from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from notifications.models import Notification
from notifications.services import notify

from .models import InspectionBooking
from .serializers import InspectionSerializer, InspectionStatusSerializer

S = InspectionBooking.Status


class InspectionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = InspectionSerializer
    filterset_fields = ["status", "property"]
    ordering_fields = ["scheduled_at", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionBooking.objects.none()
        user = self.request.user
        qs = InspectionBooking.objects.select_related("property", "user")
        if user.is_admin_role:
            return qs
        # Everyone else sees bookings they made OR bookings on their own listings.
        return qs.filter(Q(user=user) | Q(property__created_by=user))

    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        notify(booking.property.created_by, "New inspection request",
               f'{self.request.user.email} wants to inspect "{booking.property.title}" '
               f"on {booking.scheduled_at:%d %b %Y %H:%M}.", Notification.Type.INSPECTION)

    @extend_schema(request=InspectionStatusSerializer, responses=InspectionSerializer)
    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        """
        PATCH /api/inspections/{id}/status/  body: {"status": "approved"}
        * The property's agent (or an admin) can approve / reject / complete.
        * The person who booked can only cancel.
        """
        booking = self.get_object()
        data = InspectionStatusSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        new = data.validated_data["status"]

        is_manager = request.user.is_admin_role or booking.property.created_by_id == request.user.id
        if is_manager:
            allowed = {S.APPROVED, S.REJECTED, S.COMPLETED}
        elif booking.user_id == request.user.id:
            allowed = {S.CANCELLED}
        else:
            raise PermissionDenied()
        if new not in allowed:
            raise ValidationError({"status": f"You may only set: {', '.join(sorted(allowed))}."})

        booking.status = new
        booking.save(update_fields=["status"])
        notify(booking.user, f"Inspection {new}",
               f'Your inspection of "{booking.property.title}" on '
               f"{booking.scheduled_at:%d %b %Y %H:%M} is now {new}.", Notification.Type.INSPECTION)
        return Response(InspectionSerializer(booking).data)
