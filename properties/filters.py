"""
Filtering: turns URL query strings like ?min_price=500000&city=Lagos
into database filters. Built with django-filter.
"""
import django_filters as filters

from .models import Property

STATUS_ALIASES = {"sale": "for_sale", "rent": "for_rent"}


class PropertyFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    city = filters.CharFilter(lookup_expr="iexact")
    state = filters.CharFilter(lookup_expr="iexact")
    country = filters.CharFilter(lookup_expr="iexact")
    location = filters.CharFilter(method="filter_location", help_text="Matches address, city or state")
    category = filters.CharFilter(field_name="property_type__slug", lookup_expr="iexact")
    category_id = filters.NumberFilter(field_name="property_type_id")
    status = filters.CharFilter(method="filter_status", help_text="for_sale, for_rent, leased, sold (or sale / rent)")
    agent = filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = Property
        fields = ["bedrooms", "bathrooms", "featured", "is_available", "publication_status"]

    def filter_status(self, queryset, name, value):
        value = value.lower()
        return queryset.filter(status=STATUS_ALIASES.get(value, value))

    def filter_location(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(address__icontains=value) | Q(city__icontains=value) | Q(state__icontains=value)
        )
