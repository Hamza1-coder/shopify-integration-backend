from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
import json
import hmac
import hashlib
import logging

from .models import WebhookEvent
from .serializers import WebhookEventSerializer, ShopifyInventoryWebhookSerializer
from .services import WebhookProcessor
from .tasks import process_webhook_async

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ShopifyWebhookView(APIView):
    """
    Handle Shopify webhook callbacks.
    This endpoint doesn't require authentication as it's called by Shopify.
    """
    permission_classes = []  # No authentication required for webhooks
    
    def post(self, request):
        try:
            # Verify webhook authenticity (optional but recommended)
            if not self._verify_webhook(request):
                logger.warning("Invalid webhook signature received")
                return Response(
                    {'error': 'Invalid webhook signature'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Parse the webhook payload
            payload = request.data
            event_type = self._determine_event_type(request)
            
            # Create webhook event record
            webhook_event = WebhookEvent.objects.create(
                event_type=event_type,
                payload=payload,
                source='shopify'
            )
            
            # Process webhook asynchronously
            process_webhook_async.delay(webhook_event.id)
            
            logger.info(f"Received and queued webhook: {webhook_event.id}")
            
            return Response(
                {'message': 'Webhook received and queued for processing'}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _verify_webhook(self, request):
        """Verify Shopify webhook signature."""
        # In production, you should verify the webhook signature
        # This is a simplified version - implement proper verification
        webhook_secret = getattr(settings, 'SHOPIFY_WEBHOOK_SECRET', None)
        if not webhook_secret:
            return True  # Skip verification if no secret is configured
        
        signature = request.headers.get('X-Shopify-Hmac-Sha256')
        if not signature:
            return False
        
        body = request.body
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _determine_event_type(self, request):
        """Determine the event type from the webhook headers."""
        topic = request.headers.get('X-Shopify-Topic', '')
        
        if 'inventory' in topic.lower():
            return 'inventory_update'
        elif 'product' in topic.lower():
            return 'product_update'
        else:
            return 'inventory_update'  # Default to inventory update

class InventoryUpdateWebhookView(APIView):
    """Specific endpoint for inventory updates."""
    permission_classes = []
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        serializer = ShopifyInventoryWebhookSerializer(data=request.data)
        if serializer.is_valid():
            # Create webhook event
            webhook_event = WebhookEvent.objects.create(
                event_type='inventory_update',
                payload=serializer.validated_data,
                source='shopify'
            )
            
            # Process immediately for inventory updates (they're critical)
            try:
                processor = WebhookProcessor()
                result = processor.process_webhook(webhook_event)
                
                return Response({
                    'message': 'Inventory updated successfully',
                    'result': result
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to process inventory update: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WebhookEventListView(generics.ListAPIView):
    """List webhook events for monitoring."""
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['event_type', 'status', 'source']
    ordering = ['-created_at']

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def retry_webhook(request, webhook_id):
    """Retry a failed webhook."""
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_id)
        if webhook_event.status != 'failed':
            return Response(
                {'error': 'Only failed webhooks can be retried'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        webhook_event.retry_count += 1
        webhook_event.status = 'pending'
        webhook_event.error_message = None
        webhook_event.save()
        
        # Queue for processing
        process_webhook_async.delay(webhook_event.id)
        
        return Response({'message': 'Webhook queued for retry'})
        
    except WebhookEvent.DoesNotExist:
        return Response(
            {'error': 'Webhook not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
