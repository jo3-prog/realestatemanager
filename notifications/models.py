from django.conf import settings
from django.db import models


class Notification(models.Model):
    """An in-app notification (also emailed). One row = one message for one user."""

    class Type(models.TextChoices):
        AGENT = "agent", "Agent approval"
        LISTING = "listing", "Listing"
        INQUIRY = "inquiry", "Inquiry"
        INSPECTION = "inspection", "Inspection"
        REVIEW = "review", "Review"
        GENERAL = "general", "General"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.GENERAL
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"
