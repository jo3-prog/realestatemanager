from django.utils import timezone
from rest_framework import serializers

from properties.models import Property

from .models import InspectionBooking


class InspectionSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.filter(publication_status="published"))
    property_title = serializers.CharField(source="property.title", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = InspectionBooking
        fields = ["id", "property", "property_title", "user_email", "scheduled_at",
                  "note", "status", "created_at"]
        read_only_fields = ["status", "created_at"]

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Inspection must be scheduled in the future.")
        return value


class InspectionStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InspectionBooking.Status.choices)
