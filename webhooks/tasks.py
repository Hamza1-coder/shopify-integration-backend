from celery import shared_task
from django.utils import timezone
from .models import WebhookEvent
from .services import WebhookProcessor
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_webhook_async(self, webhook_event_id):
    """Process webhook event asynchronously."""
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        processor = WebhookProcessor()
        result = processor.process_webhook(webhook_event)
        
        logger.info(f"Successfully processed webhook {webhook_event_id}")
        return result
        
    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} not found")
        return
        
    except Exception as exc:
        logger.error(f"Error processing webhook {webhook_event_id}: {str(exc)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        # Max retries reached, mark as failed
        try:
            webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
            webhook_event.mark_as_failed(f"Max retries reached: {str(exc)}")
        except WebhookEvent.DoesNotExist:
            pass

@shared_task
def cleanup_old_webhooks():
    """Clean up old webhook events."""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = WebhookEvent.objects.filter(
        created_at__lt=cutoff_date,
        status='completed'
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old webhook events")
    return deleted_count
