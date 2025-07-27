from rest_framework import serializers
from .models import SearchQuery, ProductEmbedding

class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query_text', 'results_count', 'semantic_search_used',
            'processing_time', 'timestamp'
        ]

class ProductEmbeddingSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = ProductEmbedding
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'last_updated'
        ]
