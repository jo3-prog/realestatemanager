from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """Property type: Apartment, Duplex, Land, Office Space, ..."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # Slug generation: "Office Space" -> "office-space" (unique-ified if needed)
        if not self.slug:
            base = slugify(self.name)
            slug, n = base, 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Property(models.Model):
    class Status(models.TextChoices):
        FOR_SALE = "for_sale", "For Sale"
        FOR_RENT = "for_rent", "For Rent"
        LEASED = "leased", "Leased"
        SOLD = "sold", "Sold"

    class Publication(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SUSPENDED = "suspended", "Suspended by admin"

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    property_type = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="properties")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FOR_SALE)
    bedrooms = models.PositiveIntegerField(default=0)   # PositiveInteger => never below 0
    bathrooms = models.PositiveIntegerField(default=0)
    square_feet = models.PositiveIntegerField(default=0)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Nigeria")
    latitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    amenities = models.JSONField(default=list, blank=True)  # e.g. ["pool", "gym"]
    featured = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    publication_status = models.CharField(max_length=10, choices=Publication.choices, default=Publication.DRAFT)
    views_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "properties"

    def __str__(self):
        return self.title


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to="properties/%Y/%m/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "uploaded_at"]

    def __str__(self):
        return f"Image for {self.property_id}"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "property")  # can't favorite the same property twice
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} likes {self.property}"
