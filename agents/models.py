from django.conf import settings
from django.db import models


class AgentProfile(models.Model):
    """Extra information for users whose role is 'agent'. One user -> one profile."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_profile"
    )
    company_name = models.CharField(max_length=150)
    license_number = models.CharField(max_length=50)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to="agents/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_verified(self):
        """The 'verification badge' = the agent has been approved by an admin."""
        return self.status == self.Status.APPROVED

    def __str__(self):
        return f"{self.user.email} ({self.status})"
