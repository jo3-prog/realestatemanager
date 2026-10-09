from django.contrib import admin

from .models import InspectionBooking


@admin.register(InspectionBooking)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "user", "scheduled_at", "status")
    list_filter = ("status",)
