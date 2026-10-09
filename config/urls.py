"""
Root URL configuration: the "front desk" that sends each request to the
right app. Every app has its own urls.py; we plug them in here.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API endpoints
    path("api/auth/", include("accounts.urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/", include("agents.urls")),
    path("api/", include("properties.urls")),
    path("api/", include("inquiries.urls")),
    path("api/", include("inspections.urls")),
    path("api/", include("reviews.urls")),
    path("api/", include("notifications.urls")),
    path("api/analytics/", include("analytics.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    # Serve uploaded images while developing
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
