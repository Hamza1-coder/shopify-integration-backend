from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    inventory_quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    
    # AI-related fields
    embedding_cache = models.JSONField(null=True, blank=True)
    embedding_updated = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_updated']
        indexes = [
            models.Index(fields=['name', 'sku']),
            models.Index(fields=['price', 'inventory_quantity']),
            models.Index(fields=['last_updated', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_low_stock(self):
        return self.inventory_quantity < 10
    
    def update_inventory(self, quantity):
        """Update inventory with transaction safety"""
        from django.db import transaction
        with transaction.atomic():
            self.inventory_quantity = quantity
            self.save(update_fields=['inventory_quantity', 'last_updated'])

class ProductDiscount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='discounts')
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}% off"
    
    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class InventoryLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    old_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    change_reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.product.sku}: {self.old_quantity} -> {self.new_quantity}"
