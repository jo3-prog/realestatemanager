from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsApprovedAgent
from inquiries.models import Inquiry
from properties.models import Property

User = get_user_model()


class AgentAnalyticsView(APIView):
    """GET /api/analytics/agent/ : numbers about the logged-in agent's listings."""
    permission_classes = [IsApprovedAgent]

    @extend_schema(responses={200: dict})
    def get(self, request):
        listings = Property.objects.filter(created_by=request.user)
        total_views = listings.aggregate(v=Sum("views_count"))["v"] or 0
        total_inquiries = Inquiry.objects.filter(property__created_by=request.user).count()
        # Conversion rate = what % of views turned into an inquiry
        conversion = round(total_inquiries / total_views * 100, 2) if total_views else 0.0
        return Response({
            "total_listings": listings.count(),
            "published_listings": listings.filter(publication_status="published").count(),
            "total_views": total_views,
            "total_inquiries": total_inquiries,
            "conversion_rate_percent": conversion,
        })


class AdminAnalyticsView(APIView):
    """GET /api/analytics/admin/ : platform-wide numbers."""
    permission_classes = [IsAdminRole]

    @extend_schema(responses={200: dict})
    def get(self, request):
        top = Property.objects.order_by("-views_count")[:5].values("id", "title", "views_count")
        return Response({
            "total_users": User.objects.count(),
            "total_agents": User.objects.filter(role="agent").count(),
            "total_listings": Property.objects.count(),
            "most_viewed_properties": list(top),
        })
