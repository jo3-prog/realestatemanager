from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("agents", views.AgentPublicViewSet, basename="agent")

# NOTE: explicit paths are listed BEFORE the router so that
# "agents/me/" and "agents/register/" are not mistaken for "agents/<id>/".
urlpatterns = [
    path("agents/register/", views.AgentRegisterView.as_view(), name="agent-register"),
    path("agents/me/", views.AgentMeView.as_view(), name="agent-me"),
    path("admin/agents/", views.AdminAgentListView.as_view(), name="admin-agents"),
    path("admin/agents/pending/", views.PendingAgentListView.as_view(), name="admin-agents-pending"),
    path("admin/agents/<int:pk>/approve/", views.ApproveAgentView.as_view(), name="admin-agent-approve"),
    path("admin/agents/<int:pk>/reject/", views.RejectAgentView.as_view(), name="admin-agent-reject"),
] + router.urls
