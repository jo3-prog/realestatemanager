from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """POST /api/reviews/ (logged in) and GET /api/reviews/?agent=1 or ?property=2 (public)."""
    queryset = Review.objects.select_related("reviewer")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ["agent", "property", "rating"]

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)
