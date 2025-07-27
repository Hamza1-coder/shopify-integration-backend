import django_filters
from django.db.models import Q
from .models import Product

class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    sku = django_filters.CharFilter(lookup_expr='icontains')
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    inventory_min = django_filters.NumberFilter(field_name='inventory_quantity', lookup_expr='gte')
    inventory_max = django_filters.NumberFilter(field_name='inventory_quantity', lookup_expr='lte')
    is_low_stock = django_filters.BooleanFilter(method='filter_low_stock')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='last_updated', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='last_updated', lookup_expr='lte')
    
    class Meta:
        model = Product
        fields = ['is_active']
    
    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(inventory_quantity__lt=10)
        return queryset.filter(inventory_quantity__gte=10)
