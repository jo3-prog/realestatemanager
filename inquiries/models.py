from django.conf import settings
from django.db import models


class Inquiry(models.Model):
    """A message from a visitor/user to the agent about one property."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        RESPONDED = "responded", "Responded"

    property = models.ForeignKey("properties.Property", on_delete=models.CASCADE, related_name="inquiries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="inquiries")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "inquiries"

    def __str__(self):
        return f"Inquiry #{self.pk} on {self.property_id}"
