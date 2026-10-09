from django.contrib import admin

from .models import AgentProfile


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "license_number", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "company_name")
