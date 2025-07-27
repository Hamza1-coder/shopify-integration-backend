from django.db import models
from django.utils import timezone

class TaskExecution(models.Model):
    TASK_TYPES = [
        ('import_csv', 'Import CSV Data'),
        ('validate_data', 'Validate Data'),
        ('generate_report', 'Generate Report'),
        ('nightly_chain', 'Nightly Task Chain'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)  # in seconds
    result_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_type} - {self.status} ({self.created_at})"
    
    def mark_as_running(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_as_completed(self, result_data=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        if result_data:
            self.result_data = result_data
        self.save(update_fields=['status', 'completed_at', 'duration', 'result_data'])
    
    def mark_as_failed(self, error_message):
        self.status = 'failed'
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'duration', 'error_message'])
