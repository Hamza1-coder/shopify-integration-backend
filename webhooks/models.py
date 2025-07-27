from django.db import models
from django.utils import timezone
import json

class WebhookEvent(models.Model):
    EVENT_TYPES = [
        ('inventory_update', 'Inventory Update'),
        ('product_update', 'Product Update'),
        ('order_created', 'Order Created'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    source = models.CharField(max_length=100, default='shopify')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'status']),
            models.Index(fields=['created_at', 'source']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.status} ({self.created_at})"
    
    def mark_as_completed(self):
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
    
    def mark_as_failed(self, error_message):
        self.status = 'failed'
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at'])
