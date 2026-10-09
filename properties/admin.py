from django.contrib import admin

from .models import Category, Favorite, Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "status", "city", "publication_status", "featured", "created_by")
    list_filter = ("status", "publication_status", "featured", "property_type")
    search_fields = ("title", "city", "address")
    inlines = [PropertyImageInline]


admin.site.register(Favorite)
