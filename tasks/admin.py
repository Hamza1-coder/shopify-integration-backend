from django.contrib import admin
from django.utils.html import format_html
from .models import TaskExecution

@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'task_type', 'status_display', 'duration_display',
        'started_at', 'completed_at', 'created_at'
    ]
    list_filter = ['task_type', 'status', 'created_at']
    readonly_fields = [
        'task_type', 'status', 'started_at', 'completed_at',
        'duration', 'result_data', 'error_message', 'created_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_type', 'status', 'created_at')
        }),
        ('Execution Details', {
            'fields': ('started_at', 'completed_at', 'duration')
        }),
        ('Results', {
            'fields': ('result_data', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'running': 'blue',
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
    
    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration:.2f}s"
        return "-"
    duration_display.short_description = 'Duration'
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Make read-only
