from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """A rating (1-5) + comment about EITHER an agent OR a property."""

    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    agent = models.ForeignKey("agents.AgentProfile", null=True, blank=True,
                              on_delete=models.CASCADE, related_name="reviews")
    property = models.ForeignKey("properties.Property", null=True, blank=True,
                                 on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}/5 by {self.reviewer}"
