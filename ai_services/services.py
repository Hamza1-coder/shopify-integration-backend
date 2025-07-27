import spacy
import numpy as np
from sentence_transformers import SentenceTransformer
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from sklearn.metrics.pairwise import cosine_similarity
import time
import logging

from products.models import Product
from .models import SearchQuery, ProductEmbedding

logger = logging.getLogger(__name__)

class AISearchService:
    """Service for AI-powered product search."""
    
    def __init__(self):
        self.embedding_model = None
        self.spacy_model = None
        self._load_models()
    
    def _load_models(self):
        """Load AI models with caching."""
        try:
            # Load Sentence Transformer for embeddings
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            
            # Load spaCy for NLP
            spacy_model_name = getattr(settings, 'SPACY_MODEL', 'en_core_web_sm')
            self.spacy_model = spacy.load(spacy_model_name)
            
            logger.info("AI models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load AI models: {str(e)}")
            self.embedding_model = None
            self.spacy_model = None
    
    def semantic_search(self, query, limit=20):
        """Perform semantic search using embeddings."""
        if not self.embedding_model:
            logger.warning("Embedding model not available, falling back to regular search")
            return self._fallback_search(query, limit)
        
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Get all product embeddings
            product_embeddings = self._get_product_embeddings()
            
            if not product_embeddings:
                return self._fallback_search(query, limit)
            
            # Calculate similarities
            similarities = []
            for product_id, embedding in product_embeddings.items():
                similarity = cosine_similarity(
                    [query_embedding], [embedding]
                )[0][0]
                similarities.append((product_id, similarity))
            
            # Sort by similarity and get top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_product_ids = [pid for pid, _ in similarities[:limit]]
            
            # Get products maintaining order
            products = Product.objects.filter(id__in=top_product_ids, is_active=True)
            product_dict = {p.id: p for p in products}
            ordered_products = [product_dict[pid] for pid in top_product_ids if pid in product_dict]
            
            processing_time = time.time() - start_time
            
            # Log search query
            SearchQuery.objects.create(
                query_text=query,
                results_count=len(ordered_products),
                semantic_search_used=True,
                processing_time=processing_time
            )
            
            logger.info(f"Semantic search completed in {processing_time:.2f}s")
            return ordered_products
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return self._fallback_search(query, limit)
    
    def _fallback_search(self, query, limit):
        """Fallback to regular text search."""
        start_time = time.time()
        
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        )[:limit]
        
        processing_time = time.time() - start_time
        
        SearchQuery.objects.create(
            query_text=query,
            results_count=len(products),
            semantic_search_used=False,
            processing_time=processing_time
        )
        
        return list(products)
    
    def _get_product_embeddings(self):
        """Get cached product embeddings."""
        cache_key = 'product_embeddings'
        embeddings = cache.get(cache_key)
        
        if embeddings is None:
            embeddings = self._generate_product_embeddings()
            cache.set(cache_key, embeddings, settings.AI_CACHE_TIMEOUT)
        
        return embeddings
    
    def _generate_product_embeddings(self):
        """Generate embeddings for all products."""
        if not self.embedding_model:
            return {}
        
        embeddings = {}
        products = Product.objects.filter(is_active=True)
        
        for product in products:
            # Check if embedding exists and is recent
            try:
                product_embedding = ProductEmbedding.objects.get(product=product)
                # Use cached embedding if it's recent
                embeddings[product.id] = product_embedding.embedding_vector
            except ProductEmbedding.DoesNotExist:
                # Generate new embedding
                text = f"{product.name} {product.description or ''}"
                embedding = self.embedding_model.encode([text])[0].tolist()
                
                # Save embedding
                ProductEmbedding.objects.update_or_create(
                    product=product,
                    defaults={'embedding_vector': embedding}
                )
                
                embeddings[product.id] = embedding
        
        logger.info(f"Generated embeddings for {len(embeddings)} products")
        return embeddings
    
    def update_product_embedding(self, product):
        """Update embedding for a specific product."""
        if not self.embedding_model:
            return
        
        text = f"{product.name} {product.description or ''}"
        embedding = self.embedding_model.encode([text])[0].tolist()
        
        ProductEmbedding.objects.update_or_create(
            product=product,
            defaults={'embedding_vector': embedding}
        )
        
        # Invalidate cache
        cache.delete('product_embeddings')

class ProductInsightsService:
    """Service for generating product insights."""
    
    def generate_insights(self):
        """Generate comprehensive product insights."""
        insights = {}
        
        # Basic statistics
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_products = Product.objects.filter(
            is_active=True, 
            inventory_quantity__lt=10
        ).count()
        
        if total_products > 0:
            low_stock_percentage = (low_stock_products / total_products) * 100
            insights['low_stock_percentage'] = round(low_stock_percentage, 1)
        else:
            insights['low_stock_percentage'] = 0
        
        insights['total_products'] = total_products
        insights['low_stock_count'] = low_stock_products
        
        # Trending products (based on recent inventory changes)
        trending_products = self._detect_trending_products()
        insights['trending_products'] = trending_products
        
        # Price distribution insights
        price_insights = self._analyze_price_distribution()
        insights.update(price_insights)
        
        return insights
    
    def _detect_trending_products(self):
        """Detect trending products based on inventory changes."""
        from products.models import InventoryLog
        from django.utils import timezone
        from datetime import timedelta
        
        # Look at inventory changes in the last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        
        recent_logs = InventoryLog.objects.filter(
            timestamp__gte=week_ago
        ).select_related('product')
        
        # Count inventory changes per product
        product_activity = {}
        for log in recent_logs:
            product_id = log.product.id
            if product_id not in product_activity:
                product_activity[product_id] = {
                    'product': log.product,
                    'change_count': 0,
                    'total_change': 0
                }
            
            product_activity[product_id]['change_count'] += 1
            product_activity[product_id]['total_change'] += abs(
                log.new_quantity - log.old_quantity
            )
        
        # Sort by activity and return top 5
        trending = sorted(
            product_activity.values(),
            key=lambda x: x['change_count'] + (x['total_change'] / 100),
            reverse=True
        )[:5]
        
        return [
            {
                'product_id': item['product'].id,
                'name': item['product'].name,
                'sku': item['product'].sku,
                'change_count': item['change_count'],
                'current_inventory': item['product'].inventory_quantity
            }
            for item in trending
        ]
    
    def _analyze_price_distribution(self):
        """Analyze price distribution across products."""
        from django.db.models import Avg, Min, Max, Count
        
        price_stats = Product.objects.filter(is_active=True).aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            total_count=Count('id')
        )
        
        # Price ranges
        price_ranges = {
            'under_10': Product.objects.filter(is_active=True, price__lt=10).count(),
            '10_to_50': Product.objects.filter(
                is_active=True, price__gte=10, price__lt=50
            ).count(),
            '50_to_100': Product.objects.filter(
                is_active=True, price__gte=50, price__lt=100
            ).count(),
            'over_100': Product.objects.filter(is_active=True, price__gte=100).count(),
        }
        
        return {
            'price_stats': price_stats,
            'price_distribution': price_ranges
        }
