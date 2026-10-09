from rest_framework import serializers

from agents.models import AgentProfile
from properties.models import Property

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.username", read_only=True)
    agent = serializers.PrimaryKeyRelatedField(
        queryset=AgentProfile.objects.filter(status="approved"), required=False, allow_null=True)
    property = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.filter(publication_status="published"), required=False, allow_null=True)

    class Meta:
        model = Review
        fields = ["id", "reviewer_name", "agent", "property", "rating", "comment", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        agent, prop = attrs.get("agent"), attrs.get("property")
        if bool(agent) == bool(prop):
            raise serializers.ValidationError("Review EITHER an agent OR a property (not both, not neither).")
        user = self.context["request"].user
        target = {"agent": agent} if agent else {"property": prop}
        if Review.objects.filter(reviewer=user, **target).exists():
            raise serializers.ValidationError("You have already reviewed this.")
        if agent and agent.user_id == user.id:
            raise serializers.ValidationError("You cannot review yourself.")
        if prop and prop.created_by_id == user.id:
            raise serializers.ValidationError("You cannot review your own listing.")
        return attrs
