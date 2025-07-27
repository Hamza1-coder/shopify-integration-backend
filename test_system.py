#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopify_backend.settings')
django.setup()

import requests
from django.contrib.auth.models import User, Group
from django.core.management import execute_from_command_line
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

def test_system_functionality():
    """Test the complete system functionality."""
    print("🔍 Testing Shopify Integration Backend System")
    print("=" * 50)
    
    # 1. Test Database and Models
    print("\n1. Testing Database and Models...")
    test_models()
    
    # 2. Test API Endpoints
    print("\n2. Testing API Endpoints...")
    test_api_endpoints()
    
    # 3. Test AI Services
    print("\n3. Testing AI Services...")
    test_ai_services()
    
    # 4. Test Celery Tasks
    print("\n4. Testing Celery Tasks...")
    test_celery_tasks()
    
    # 5. Test Webhook Processing
    print("\n5. Testing Webhook Processing...")
    test_webhook_processing()
    
    print("\n✅ System testing completed!")

def test_models():
    """Test model creation and relationships."""
    from products.models import Product, ProductDiscount, InventoryLog
    from webhooks.models import WebhookEvent
    from tasks.models import TaskExecution
    
    # Test product creation
    product_count = Product.objects.count()
    print(f"   📊 Products in database: {product_count}")
    
    # Test webhook events
    webhook_count = WebhookEvent.objects.count()
    print(f"   🪝 Webhook events: {webhook_count}")
    
    # Test task executions
    task_count = TaskExecution.objects.count()
    print(f"   ⚙️ Task executions: {task_count}")

def test_api_endpoints():
    """Test API endpoints with proper authentication."""
    from rest_framework.test import APIClient
    from django.contrib.auth.models import User
    import json
    
    try:
        # Create or get test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com', 'is_staff': True}
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        # Add user to API Users group
        api_group, _ = Group.objects.get_or_create(name='API Users')
        user.groups.add(api_group)
        
        client = APIClient()
        client.credentials(HTTP_HOST='localhost:8000')  # Set the host header
        
        # Test login
        login_success = client.login(username='testuser', password='testpass123')
        print(f"   🔑 Login {'succeeded' if login_success else 'failed'}")
        
        # Test product endpoints
        response = client.get('http://localhost:8000/api/v1/products/')
        data = json.loads(response.content)
        print(f"   📦 Products list: {response.status_code} - {len(data.get('results', []))} products")
        
        response = client.get('http://localhost:8000/api/v1/products/search/?q=phone')
        data = json.loads(response.content)
        print(f"   🔍 Product search: {response.status_code} - {len(data)} results")
        
        response = client.get('http://localhost:8000/api/v1/products/stats/')
        print(f"   📈 Product stats: {response.status_code}")
        
        # Test AI endpoints
        try:
            response = client.get('http://localhost:8000/api/v1/ai/search/?q=laptop')
            print(f"   🤖 AI search: {response.status_code}")
            
            response = client.get('http://localhost:8000/api/v1/ai/insights/')
            print(f"   💡 AI insights: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ AI endpoints not available: {str(e)}")
            
    except Exception as e:
        print(f"   ❌ API test error: {str(e)}")
    finally:
        # Clean up
        if 'user' in locals():
            user.delete()

def test_ai_services():
    """Test AI service functionality."""
    from ai_services.services import AISearchService, ProductInsightsService
    
    try:
        # Test semantic search
        ai_search = AISearchService()
        results = ai_search.semantic_search("mobile device", limit=3)
        print(f"   🔍 Semantic search results: {len(results)} products found")
        
        # Test insights generation
        insights_service = ProductInsightsService()
        insights = insights_service.generate_insights()
        print(f"   📊 Generated insights: {len(insights)} metrics")
        
    except Exception as e:
        print(f"   ❌ AI services error: {str(e)}")

def test_celery_tasks():
    """Test Celery task execution."""
    from tasks.tasks import import_csv_data
    from celery import current_app
    
    try:
        # Check if Celery is running
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print(f"   ✅ Celery workers active: {len(active_workers)}")
            
            # Test CSV import task
            result = import_csv_data.delay()
            task_result = result.get(timeout=30)
            print(f"   📁 CSV import test: {task_result['status']}")
        else:
            print("   ⚠️ No active Celery workers found")
            
    except Exception as e:
        print(f"   ❌ Celery error: {str(e)}")

def test_webhook_processing():
    """Test webhook processing functionality."""
    from webhooks.models import WebhookEvent
    from webhooks.services import WebhookProcessor
    
    try:
        # Create test webhook
        webhook = WebhookEvent.objects.create(
            event_type='inventory_update',
            payload={'sku': 'IP14-128', 'available': 30},
            source='shopify'
        )
        
        # Process webhook
        processor = WebhookProcessor()
        result = processor.process_webhook(webhook)
        
        print(f"   🪝 Webhook processing: Success - Updated {result.get('sku', 'unknown')}")
        
    except Exception as e:
        print(f"   ❌ Webhook processing error: {str(e)}")

if __name__ == '__main__':
    test_system_functionality()
