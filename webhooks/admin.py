from django.contrib import admin
from django.utils.html import format_html
from .models import WebhookEvent

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'event_type', 'status_display', 'source',
        'retry_count', 'created_at', 'processed_at'
    ]
    list_filter = ['event_type', 'status', 'source', 'created_at']
    search_fields = ['event_type', 'source']
    readonly_fields = ['created_at', 'processed_at', 'payload']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'source', 'status')
        }),
        ('Processing Details', {
            'fields': ('retry_count', 'error_message', 'created_at', 'processed_at')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.status.title()
        )
    status_display.short_description = 'Status'
    
    actions = ['retry_failed_webhooks']
    
    def retry_failed_webhooks(self, request, queryset):
        failed_webhooks = queryset.filter(status='failed')
        count = 0
        for webhook in failed_webhooks:
            webhook.status = 'pending'
            webhook.retry_count += 1
            webhook.error_message = None
            webhook.save()
            count += 1
        
        self.message_user(request, f'{count} failed webhooks queued for retry.')
    retry_failed_webhooks.short_description = 'Retry failed webhooks'
