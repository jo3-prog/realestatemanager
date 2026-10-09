from django.db.models import F, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsApprovedAgentOrAdmin, IsOwnerOrAdmin
from notifications.models import Notification
from notifications.services import notify

from .filters import PropertyFilter
from .models import Category, Favorite, Property, PropertyImage
from .serializers import (
    CategorySerializer,
    FavoriteSerializer,
    ImageUploadSerializer,
    PropertyImageSerializer,
    PropertySerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """Categories: everyone can read, only admins can create/update/delete."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdminRole()]


class PropertyViewSet(viewsets.ModelViewSet):
    
    serializer_class = PropertySerializer
    filterset_class = PropertyFilter
    search_fields = ["title", "description", "address", "city", "state", "country", "property_type__name"]
    ordering_fields = ["price", "created_at", "bedrooms", "bathrooms", "square_feet", "views_count"]

    # ---- who can see what -------------------------------------------------
    def get_queryset(self):
        qs = Property.objects.select_related("property_type", "created_by").prefetch_related("images")
        if getattr(self, "swagger_fake_view", False):
            return qs.none()
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return qs                                   # admins see everything
        published = Q(publication_status=Property.Publication.PUBLISHED)
        if user.is_authenticated:
            return qs.filter(published | Q(created_by=user))  # + your own drafts
        return qs.filter(published)                     # visitors: published only

    # ---- who can do what --------------------------------------------------
    def get_permissions(self):
        if self.action in ("list", "retrieve", "featured", "compare"):
            return [AllowAny()]
        if self.action in ("suspend", "reinstate", "feature", "unfeature"):
            return [IsAdminRole()]
        # create, update, delete, images, mine: approved agent (or admin)...
        # ...and for a single object, it must be THEIR listing (IsOwnerOrAdmin).
        return [IsApprovedAgentOrAdmin(), IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)   # the logged-in agent owns it

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Count a "view" (used by analytics) unless the owner is looking.
        if instance.created_by_id != request.user.id:
            Property.objects.filter(pk=instance.pk).update(views_count=F("views_count") + 1)
            instance.refresh_from_db(fields=["views_count"])
        return Response(self.get_serializer(instance).data)

    # ---- extra endpoints --------------------------------------------------
    @extend_schema(responses=PropertySerializer(many=True))
    @action(detail=False, methods=["get"])
    def mine(self, request):
        """GET /api/properties/mine/ : the agent's own listings (all statuses)."""
        qs = self.filter_queryset(self.get_queryset().filter(created_by=request.user))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(responses=PropertySerializer(many=True))
    @action(detail=False, methods=["get"])
    def featured(self, request):
        """GET /api/properties/featured/"""
        qs = self.filter_queryset(self.get_queryset().filter(
            featured=True, publication_status=Property.Publication.PUBLISHED))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(parameters=[OpenApiParameter("ids", str, description="Comma separated, e.g. 1,2,3 (max 4)")],
                   responses=PropertySerializer(many=True))
    @action(detail=False, methods=["get"])
    def compare(self, request):
        """GET /api/properties/compare/?ids=1,2,3 : side-by-side comparison."""
        try:
            ids = [int(i) for i in request.query_params.get("ids", "").split(",") if i.strip()]
        except ValueError:
            raise ValidationError({"ids": "Use comma separated numbers."})
        if not 2 <= len(ids) <= 4:
            raise ValidationError({"ids": "Provide between 2 and 4 property ids."})
        props = self.get_queryset().filter(pk__in=ids)
        return Response(self.get_serializer(props, many=True).data)

    @extend_schema(request={"multipart/form-data": ImageUploadSerializer},
                   responses=PropertyImageSerializer(many=True))
    @action(detail=True, methods=["post"], parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def images(self, request, pk=None):
        """POST /api/properties/{id}/images/ : upload one or MANY images (field name: images)."""
        prop = self.get_object()
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        has_primary = prop.images.filter(is_primary=True).exists()
        created = []
        for i, f in enumerate(serializer.validated_data["images"]):
            created.append(PropertyImage.objects.create(
                property=prop, image=f, is_primary=(not has_primary and i == 0)))
        return Response(PropertyImageSerializer(created, many=True, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>\d+)")
    def delete_image(self, request, pk=None, image_id=None):
        """DELETE /api/properties/{id}/images/{image_id}/"""
        prop = self.get_object()
        deleted, _ = prop.images.filter(pk=image_id).delete()
        if not deleted:
            return Response({"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _admin_toggle(self, request, field, value, message):
        prop = self.get_object()
        setattr(prop, field, value)
        prop.save(update_fields=[field, "updated_at"])
        if message:
            notify(prop.created_by, "Listing update", f'Your listing "{prop.title}" {message}.',
                   Notification.Type.LISTING)
        return Response(self.get_serializer(prop).data)

    @extend_schema(request=None, responses=PropertySerializer)
    @action(detail=True, methods=["patch"])
    def suspend(self, request, pk=None):
        """PATCH /api/properties/{id}/suspend/ (admin)"""
        return self._admin_toggle(request, "publication_status", Property.Publication.SUSPENDED,
                                  "was suspended by an administrator")

    @extend_schema(request=None, responses=PropertySerializer)
    @action(detail=True, methods=["patch"])
    def reinstate(self, request, pk=None):
        """PATCH /api/properties/{id}/reinstate/ (admin): back to published."""
        return self._admin_toggle(request, "publication_status", Property.Publication.PUBLISHED,
                                  "was reinstated and is live again")

    @extend_schema(request=None, responses=PropertySerializer)
    @action(detail=True, methods=["patch"])
    def feature(self, request, pk=None):
        """PATCH /api/properties/{id}/feature/ (admin)"""
        return self._admin_toggle(request, "featured", True, "is now a featured property")

    @extend_schema(request=None, responses=PropertySerializer)
    @action(detail=True, methods=["patch"])
    def unfeature(self, request, pk=None):
        """PATCH /api/properties/{id}/unfeature/ (admin)"""
        return self._admin_toggle(request, "featured", False, None)


class FavoriteViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Save / list / remove favorites. Each user only sees their own."""
    serializer_class = FavoriteSerializer
    filterset_fields = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Favorite.objects.none()
        return Favorite.objects.filter(user=self.request.user).select_related("property")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
