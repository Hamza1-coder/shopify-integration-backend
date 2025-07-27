from django.db.models import Q, Avg, Count, Sum
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import logging

from .models import Product, ProductDiscount, InventoryLog
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    ProductDiscountSerializer, ProductDiscountCreateSerializer,
    InventoryLogSerializer, BulkPriceUpdateSerializer
)
from .filters import ProductFilter

logger = logging.getLogger(__name__)

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.select_related().prefetch_related('discounts')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'price', 'inventory_quantity', 'last_updated', 'created_at']
    ordering = ['-last_updated']
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def perform_create(self, serializer):
        product = serializer.save()
        logger.info(f"Created product: {product.name} ({product.sku})")

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related().prefetch_related('discounts')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        new_instance = serializer.save()
        
        # Log inventory changes
        if old_instance.inventory_quantity != new_instance.inventory_quantity:
            InventoryLog.objects.create(
                product=new_instance,
                old_quantity=old_instance.inventory_quantity,
                new_quantity=new_instance.inventory_quantity,
                change_reason="Manual update via API"
            )
        
        logger.info(f"Updated product: {new_instance.name} ({new_instance.sku})")

class ProductSearchView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Product.objects.none()
        
        return Product.objects.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

class BulkPriceUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BulkPriceUpdateSerializer(data=request.data)
        if serializer.is_valid():
            product_ids = serializer.validated_data['product_ids']
            adjustment_type = serializer.validated_data['price_adjustment_type']
            adjustment_value = serializer.validated_data['adjustment_value']
            
            with transaction.atomic():
                products = Product.objects.filter(id__in=product_ids)
                updated_count = 0
                
                for product in products:
                    old_price = product.price
                    if adjustment_type == 'percentage':
                        product.price = old_price * (1 + adjustment_value / 100)
                    else:  # fixed
                        product.price = old_price + adjustment_value
                    
                    product.save(update_fields=['price', 'last_updated'])
                    updated_count += 1
                
                logger.info(f"Bulk updated prices for {updated_count} products")
                
                return Response({
                    'message': f'Successfully updated {updated_count} products',
                    'updated_count': updated_count
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductDiscountListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductDiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return ProductDiscount.objects.filter(product_id=product_id)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductDiscountCreateSerializer
        return ProductDiscountSerializer
    
    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = generics.get_object_or_404(Product, id=product_id)
        serializer.save(product=product)

class ProductStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        stats = Product.objects.aggregate(
            total_products=Count('id'),
            avg_price=Avg('price'),
            total_inventory=Sum('inventory_quantity'),
            low_stock_count=Count('id', filter=Q(inventory_quantity__lt=10))
        )
        
        stats['low_stock_percentage'] = (
            (stats['low_stock_count'] / stats['total_products']) * 100 
            if stats['total_products'] > 0 else 0
        )
        
        return Response(stats)

class InventoryLogListView(generics.ListAPIView):
    serializer_class = InventoryLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['product']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        if product_id:
            return InventoryLog.objects.filter(product_id=product_id)
        return InventoryLog.objects.all()
