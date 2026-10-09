from django.urls import path

from . import views

urlpatterns = [
    path("agent/", views.AgentAnalyticsView.as_view(), name="analytics-agent"),
    path("admin/", views.AdminAnalyticsView.as_view(), name="analytics-admin"),
]
