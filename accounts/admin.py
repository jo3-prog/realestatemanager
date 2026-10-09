from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Add our extra fields to the built-in user admin page
    fieldsets = UserAdmin.fieldsets + (
        ("Real estate", {"fields": ("role", "phone_number", "is_email_verified")}),
    )
    list_display = ("email", "username", "role", "is_active", "is_email_verified")
    list_filter = ("role", "is_active", "is_email_verified")
    search_fields = ("email", "username")
