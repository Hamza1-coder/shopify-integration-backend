from django.urls import path
from . import views

urlpatterns = [
    # Shopify webhook endpoints
    path('shopify/', views.ShopifyWebhookView.as_view(), name='shopify-webhook'),
    path('inventory-update/', views.InventoryUpdateWebhookView.as_view(), name='inventory-webhook'),
    
    # Webhook management
    path('events/', views.WebhookEventListView.as_view(), name='webhook-events'),
    path('events/<int:webhook_id>/retry/', views.retry_webhook, name='retry-webhook'),
]
