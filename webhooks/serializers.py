from rest_framework import serializers
from .models import WebhookEvent

class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = [
            'id', 'event_type', 'payload', 'status', 'source',
            'processed_at', 'created_at', 'error_message', 'retry_count'
        ]
        read_only_fields = [
            'id', 'status', 'processed_at', 'created_at', 'error_message', 'retry_count'
        ]

class ShopifyInventoryWebhookSerializer(serializers.Serializer):
    inventory_item_id = serializers.CharField()
    location_id = serializers.CharField()
    available = serializers.IntegerField()
    sku = serializers.CharField(required=False, allow_blank=True)
    product_id = serializers.CharField(required=False, allow_blank=True)
    
    def validate_available(self, value):
        if value < 0:
            raise serializers.ValidationError("Available quantity cannot be negative.")
        return value
