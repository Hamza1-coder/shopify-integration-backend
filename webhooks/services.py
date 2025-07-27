from django.db import transaction
from django.utils import timezone
from products.models import Product, InventoryLog
from .models import WebhookEvent
import logging

logger = logging.getLogger(__name__)

class WebhookProcessor:
    """Service class to process different types of webhooks."""
    
    def __init__(self):
        self.processors = {
            'inventory_update': self.process_inventory_update,
            'product_update': self.process_product_update,
        }
    
    def process_webhook(self, webhook_event):
        """Main method to process webhook events."""
        try:
            webhook_event.status = 'processing'
            webhook_event.save(update_fields=['status'])
            
            processor = self.processors.get(webhook_event.event_type)
            if not processor:
                raise ValueError(f"No processor found for event type: {webhook_event.event_type}")
            
            result = processor(webhook_event.payload)
            webhook_event.mark_as_completed()
            
            logger.info(f"Successfully processed webhook {webhook_event.id}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            webhook_event.mark_as_failed(error_msg)
            logger.error(f"Failed to process webhook {webhook_event.id}: {error_msg}")
            raise
    
    def process_inventory_update(self, payload):
        """Process Shopify inventory update webhook."""
        sku = payload.get('sku')
        available_quantity = payload.get('available', 0)
        
        if not sku:
            raise ValueError("SKU is required for inventory update")
        
        with transaction.atomic():
            try:
                product = Product.objects.select_for_update().get(sku=sku)
                old_quantity = product.inventory_quantity
                
                product.update_inventory(available_quantity)
                
                # Create inventory log
                InventoryLog.objects.create(
                    product=product,
                    old_quantity=old_quantity,
                    new_quantity=available_quantity,
                    change_reason="Shopify webhook update"
                )
                
                logger.info(f"Updated inventory for {sku}: {old_quantity} -> {available_quantity}")
                
                return {
                    'product_id': product.id,
                    'sku': sku,
                    'old_quantity': old_quantity,
                    'new_quantity': available_quantity
                }
                
            except Product.DoesNotExist:
                logger.warning(f"Product with SKU {sku} not found for inventory update")
                raise ValueError(f"Product with SKU {sku} not found")
    
    def process_product_update(self, payload):
        """Process general product update webhook."""
        # Implementation for product updates
        # This can be extended based on specific requirements
        product_id = payload.get('product_id')
        if not product_id:
            raise ValueError("Product ID is required for product update")
        
        # Add your product update logic here
        logger.info(f"Processed product update for ID: {product_id}")
        return {'product_id': product_id, 'status': 'updated'}
