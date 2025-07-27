from rest_framework import serializers
from django.utils import timezone
from .models import Product, ProductDiscount, InventoryLog

class ProductListSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'price', 'inventory_quantity',
            'last_updated', 'is_active', 'is_low_stock'
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.ReadOnlyField()
    discounts = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'price', 'inventory_quantity',
            'description', 'last_updated', 'created_at', 'is_active',
            'is_low_stock', 'discounts'
        ]
    
    def get_discounts(self, obj):
        active_discounts = obj.discounts.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        return ProductDiscountSerializer(active_discounts, many=True).data

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'price', 'inventory_quantity',
            'description', 'is_active'
        ]
    
    def validate_sku(self, value):
        instance = self.instance
        if Product.objects.filter(sku=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError("Product with this SKU already exists.")
        return value

class ProductDiscountSerializer(serializers.ModelSerializer):
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductDiscount
        fields = [
            'id', 'discount_percentage', 'start_date', 'end_date',
            'is_active', 'is_valid', 'created_at'
        ]

class ProductDiscountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDiscount
        fields = [
            'product', 'discount_percentage', 'start_date', 'end_date', 'is_active'
        ]
    
    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data

class InventoryLogSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = InventoryLog
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'old_quantity', 'new_quantity', 'change_reason', 'timestamp'
        ]

class BulkPriceUpdateSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    price_adjustment_type = serializers.ChoiceField(
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]
    )
    adjustment_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_product_ids(self, value):
        existing_ids = set(Product.objects.filter(id__in=value).values_list('id', flat=True))
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(f"Invalid product IDs: {list(invalid_ids)}")
        return value
