from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # extending django's user model to add a role and email verification status

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        AGENT = "agent", "Agent"
        USER = "user", "User / Visitor"

    email = models.EmailField(unique=True)  # validation rule: email must be unique
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    phone_number = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"  # log in with email instead of username
    REQUIRED_FIELDS = ["username"]  # asked for by `createsuperuser`

    def save(self, *args, **kwargs):
        # Anyone created with `createsuperuser` is automatically an admin.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    # Handy shortcuts used by the permission classes
    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_approved_agent(self):
        profile = getattr(self, "agent_profile", None)
        return (
            self.role == self.Role.AGENT
            and profile is not None
            and profile.status == "approved"
        )

    def __str__(self):
        return self.email
