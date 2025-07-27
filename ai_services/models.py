from django.db import models
from django.utils import timezone

class SearchQuery(models.Model):
    query_text = models.TextField()
    results_count = models.PositiveIntegerField()
    semantic_search_used = models.BooleanField(default=False)
    processing_time = models.FloatField()  # in seconds
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"'{self.query_text[:50]}...' - {self.results_count} results"

class ProductEmbedding(models.Model):
    product = models.OneToOneField(
        'products.Product', 
        on_delete=models.CASCADE,
        related_name='embedding'
    )
    embedding_vector = models.JSONField()
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"Embedding for {self.product.name}"
