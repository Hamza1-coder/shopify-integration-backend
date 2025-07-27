from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.SemanticSearchView.as_view(), name='semantic-search'),
    path('insights/', views.ProductInsightsView.as_view(), name='product-insights'),
    path('search-analytics/', views.SearchAnalyticsView.as_view(), name='search-analytics'),
    path('refresh-embeddings/', views.RefreshEmbeddingsView.as_view(), name='refresh-embeddings'),
]
