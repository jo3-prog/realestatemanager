from django.db.models import Avg
from rest_framework import serializers

from .models import Category, Favorite, Property, PropertyImage

MAX_IMAGE_MB = 5


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]
        read_only_fields = ["slug"]


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ["id", "image", "caption", "is_primary", "uploaded_at"]
        read_only_fields = fields


class ImageUploadSerializer(serializers.Serializer):
    """Validates a batch of uploaded images."""
    images = serializers.ListField(child=serializers.ImageField(), allow_empty=False)
    # ImageField already checks the file is a REAL image (via Pillow).

    def validate_images(self, files):
        for f in files:
            if f.size > MAX_IMAGE_MB * 1024 * 1024:
                raise serializers.ValidationError(f"{f.name} is larger than {MAX_IMAGE_MB}MB.")
            ext = f.name.rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "webp"):
                raise serializers.ValidationError(f"{f.name}: only jpg, jpeg, png, webp allowed.")
        return files


class PropertySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="property_type.name", read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    agent_email = serializers.EmailField(source="created_by.email", read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id", "title", "description", "price", "property_type", "category_name",
            "status", "bedrooms", "bathrooms", "square_feet", "address", "city",
            "state", "country", "latitude", "longitude", "amenities", "featured",
            "is_available", "publication_status", "views_count", "images",
            "created_by", "agent_email", "average_rating", "created_at", "updated_at",
        ]
        # Fields the client is NOT allowed to set:
        read_only_fields = ["featured", "views_count", "created_by", "created_at", "updated_at"]

    def get_average_rating(self, obj) -> float | None:
        avg = obj.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(avg, 2) if avg else None

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_amenities(self, value):
        if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
            raise serializers.ValidationError('Amenities must be a list of text values, e.g. ["pool", "gym"].')
        return value

    def validate_publication_status(self, value):
        # Only admins can suspend; an agent can only choose draft or published.
        request = self.context.get("request")
        if value == Property.Publication.SUSPENDED and not (request and request.user.is_admin_role):
            raise serializers.ValidationError("Only an admin can suspend a listing.")
        return value

    def validate(self, attrs):
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if (lat is None) != (lng is None) and not self.partial:
            raise serializers.ValidationError("Provide both latitude and longitude, or neither.")
        return attrs


class FavoriteSerializer(serializers.ModelSerializer):
    property_detail = PropertySerializer(source="property", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "property", "property_detail", "created_at"]
        read_only_fields = ["created_at"]
        validators = []  # we do our own duplicate check below (friendlier message)

    def validate_property(self, prop):
        if prop.publication_status != Property.Publication.PUBLISHED:
            raise serializers.ValidationError("This property is not available.")
        if Favorite.objects.filter(user=self.context["request"].user, property=prop).exists():
            raise serializers.ValidationError("Already in your favorites.")
        return prop
