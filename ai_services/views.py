from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
import time

from products.serializers import ProductListSerializer
from .services import AISearchService, ProductInsightsService
from .models import SearchQuery
from .serializers import SearchQuerySerializer

class SemanticSearchView(generics.ListAPIView):
    """AI-powered semantic search for products."""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return []
        
        ai_search = AISearchService()
        return ai_search.semantic_search(query, limit=20)
    
    def list(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        if not query:
            return Response({
                'results': [],
                'message': 'Please provide a search query using the "q" parameter'
            })
        
        start_time = time.time()
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        processing_time = time.time() - start_time
        
        return Response({
            'results': serializer.data,
            'query': query,
            'count': len(serializer.data),
            'processing_time': round(processing_time, 3),
            'semantic_search': True
        })

class ProductInsightsView(APIView):
    """Generate AI-powered product insights."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Check cache first
        cache_key = 'product_insights'
        insights = cache.get(cache_key)
        
        if insights is None:
            insights_service = ProductInsightsService()
            insights = insights_service.generate_insights()
            
            # Cache for 1 hour
            cache.set(cache_key, insights, 3600)
        
        return Response({
            'insights': insights,
            'cached': cache.get(cache_key) is not None,
            'timestamp': time.time()
        })

class SearchAnalyticsView(generics.ListAPIView):
    """Analytics for search queries."""
    queryset = SearchQuery.objects.all()
    serializer_class = SearchQuerySerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-timestamp']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by semantic search usage
        semantic_only = self.request.query_params.get('semantic_only')
        if semantic_only == 'true':
            queryset = queryset.filter(semantic_search_used=True)
        elif semantic_only == 'false':
            queryset = queryset.filter(semantic_search_used=False)
        
        return queryset

class RefreshEmbeddingsView(APIView):
    """Manually refresh product embeddings."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        ai_search = AISearchService()
        
        # Clear cache and regenerate embeddings
        cache.delete('product_embeddings')
        embeddings = ai_search._generate_product_embeddings()
        
        return Response({
            'message': f'Refreshed embeddings for {len(embeddings)} products',
            'count': len(embeddings)
        })
