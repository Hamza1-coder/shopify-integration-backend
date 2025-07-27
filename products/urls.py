from django.urls import path
from . import views

urlpatterns = [
    # Product CRUD
    path('', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('search/', views.ProductSearchView.as_view(), name='product-search'),
    path('stats/', views.ProductStatsView.as_view(), name='product-stats'),
    
    # Bulk operations
    path('bulk-price-update/', views.BulkPriceUpdateView.as_view(), name='bulk-price-update'),
    
    # Discounts
    path('<int:product_id>/discounts/', views.ProductDiscountListCreateView.as_view(), name='product-discounts'),
    
    # Inventory logs
    path('inventory-logs/', views.InventoryLogListView.as_view(), name='inventory-logs'),
    path('<int:product_id>/inventory-logs/', views.InventoryLogListView.as_view(), name='product-inventory-logs'),
]
