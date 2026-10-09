from rest_framework import serializers

from properties.models import Property

from .models import Inquiry


class InquirySerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.filter(publication_status="published"))
    property_title = serializers.CharField(source="property.title", read_only=True)

    class Meta:
        model = Inquiry
        fields = ["id", "property", "property_title", "name", "email", "phone_number",
                  "message", "status", "response", "responded_at", "created_at"]
        read_only_fields = ["status", "response", "responded_at", "created_at"]


class InquiryResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
