from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Product, ProductDiscount, InventoryLog
from rangefilter.filters import NumericRangeFilter

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'sku', 'price', 'inventory_quantity', 
        'is_low_stock_display', 'is_active', 'last_updated'
    ]
    list_filter = [
        'is_active', 'last_updated', 'created_at',
        ('price', NumericRangeFilter),
        ('inventory_quantity', NumericRangeFilter),
    ]
    search_fields = ['name', 'sku', 'description']
    ordering = ['-last_updated']
    list_editable = ['price', 'inventory_quantity', 'is_active']
    readonly_fields = ['created_at', 'last_updated']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'description', 'is_active')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'inventory_quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['bulk_activate', 'bulk_deactivate', 'bulk_price_increase']
    
    def is_low_stock_display(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: red;">⚠️ Low Stock</span>')
        return format_html('<span style="color: green;">✅ In Stock</span>')
    is_low_stock_display.short_description = 'Stock Status'
    
    def bulk_activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated.')
    bulk_activate.short_description = 'Activate selected products'
    
    def bulk_deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    bulk_deactivate.short_description = 'Deactivate selected products'
    
    def bulk_price_increase(self, request, queryset):
        # Increase price by 10%
        for product in queryset:
            product.price *= 1.1
            product.save()
        self.message_user(request, f'{queryset.count()} product prices increased by 10%.')
    bulk_price_increase.short_description = 'Increase prices by 10%%'

@admin.register(ProductDiscount)
class ProductDiscountAdmin(admin.ModelAdmin):
    list_display = ['product', 'discount_percentage', 'start_date', 'end_date', 'is_active', 'is_valid']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['product__name', 'product__sku']
    date_hierarchy = 'start_date'

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ['product', 'old_quantity', 'new_quantity', 'change_reason', 'timestamp']
    list_filter = ['timestamp', 'change_reason']
    search_fields = ['product__name', 'product__sku']
    readonly_fields = ['product', 'old_quantity', 'new_quantity', 'change_reason', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Make read-only
