from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg
from rest_framework import serializers

from accounts.serializers import RegisterSerializer
from accounts.services import send_verification_email
from notifications.models import Notification
from notifications.services import notify

from .models import AgentProfile

User = get_user_model()


class AgentRegisterSerializer(RegisterSerializer):
    """Same as normal registration + the agent's business details."""

    company_name = serializers.CharField(max_length=150, write_only=True)
    license_number = serializers.CharField(max_length=50, write_only=True)
    bio = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta(RegisterSerializer.Meta):
        fields = RegisterSerializer.Meta.fields + ["company_name", "license_number", "bio"]

    @transaction.atomic  # either BOTH the user and profile are saved, or neither
    def create(self, validated_data):
        profile_data = {
            key: validated_data.pop(key)
            for key in ("company_name", "license_number", "bio")
            if key in validated_data
        }
        user = User.objects.create_user(role=User.Role.AGENT, **validated_data)
        AgentProfile.objects.create(user=user, **profile_data)
        send_verification_email(user)
        for admin in User.objects.filter(role=User.Role.ADMIN):
            notify(admin, "New agent application",
                   f"{user.email} applied to become an agent.", Notification.Type.AGENT)
        return user


class AgentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)  # the verification badge
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfile
        fields = ["id", "email", "full_name", "phone_number", "company_name",
                  "license_number", "bio", "profile_photo", "status", "is_verified",
                  "rejection_reason", "average_rating", "created_at", "reviewed_at"]
        read_only_fields = ["id", "status", "rejection_reason", "created_at", "reviewed_at"]

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_average_rating(self, obj) -> float | None:
        avg = obj.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(avg, 2) if avg else None


class AgentDecisionSerializer(serializers.Serializer):
    """Body for the reject endpoint (optional reason)."""
    reason = serializers.CharField(required=False, allow_blank=True)
