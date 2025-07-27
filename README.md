# Shopify Integration Backend

A comprehensive Django REST Framework backend system that integrates with Shopify for product management, webhook processing, and AI-powered insights.

## 🚀 Features

- **REST API**: Complete CRUD operations for product management
- **Shopify Integration**: Real-time webhook processing for inventory updates
- **AI-Powered Search**: Semantic search using Sentence Transformers
- **Background Tasks**: Automated nightly data processing with Celery
- **Smart Insights**: AI-generated product analytics and trending detection
- **Admin Interface**: Customized Django admin with bulk operations
- **Docker Ready**: Fully containerized for easy deployment

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## 🏃‍♂️ Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (if running locally)
- Redis (for Celery)

### 🔧 Setup & Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Hamza1-coder/shopify-integration-backend.git
   cd shopify-integration-backend
   ```

2. **Build Docker containers**

   ```bash
   docker-compose build
   ```

3. **Start all services**

   ```bash
   docker-compose up
   ```

4. **Setup database (in separate terminal)**

   ```bash
   # Create migrations
   docker-compose exec web python manage.py makemigrations
   docker-compose exec web python manage.py migrate

   # Create superuser
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Configure API access**

   ```bash
   docker-compose exec web python manage.py shell
   ```

   ```python
   from django.contrib.auth.models import Group, User
   api_group = Group.objects.create(name='API Users')
   user = User.objects.get(username='your_superuser_name')
   user.groups.add(api_group)
   exit()
   ```

6. **Test the system**

   ```bash
   docker-compose exec web python test_system.py
   ```

### 🌐 Setting up Ngrok for Shopify Webhooks

Since Shopify needs to send webhooks to your local development server, you'll need to expose your local server to the internet using ngrok.

1. **Install ngrok**

   - Download from [ngrok.com](https://ngrok.com/) or use package manager:

     **macOS with Homebrew**

     ```bash
     brew install ngrok/ngrok/ngrok
     ```

     **Windows with Chocolatey**

     ```bash
     choco install ngrok
     ```

     Or download directly from <https://ngrok.com/download>

2. **Start your Django server**

   ```bash
   docker-compose up
   ```

3. **Expose your local server (in a new terminal)**

   ```bash
   ngrok http 8000
   ```

4. **Copy the ngrok URL**

   Example output:

   ```plaintext
   Session Status    online
   Account           Your Name (Plan: Free)
   Version           3.0.0
   Region            United States (us)
   Latency           -
   Web Interface     http://127.0.0.1:4040
   Forwarding        https://86c5050a970b.ngrok-free.app -> http://localhost:8000
   ```

5. **Configure Shopify Webhooks**

   In your Shopify admin panel, set up webhooks pointing to:

   - Product updates: `https://your-ngrok-url.ngrok-free.app/api/v1/webhooks/shopify/`
   - Inventory updates: `https://your-ngrok-url.ngrok-free.app/api/v1/webhooks/inventory-update/`

6. **Add Webhook Secret to Environment**

   Add to your `.env` file:

   ```plaintext
   SHOPIFY_WEBHOOK_SECRET=your_shopify_api_secret_key
   ```

   **Important Notes:**

   - Free ngrok URLs change every time you restart ngrok
   - For production, use a paid ngrok plan or deploy to a cloud service
   - The ngrok web interface at `http://127.0.0.1:4040` shows incoming webhook requests for debugging

### 🌐 Access Points

- **API Base URL**: `http://localhost:8000/api/v1/`
- **Admin Interface**: `http://localhost:8000/admin/`

## 📚 API Documentation

### Core Endpoints

#### Products API

- `GET /api/v1/products/` - List all products
- `POST /api/v1/products/` - Create new product
- `GET /api/v1/products/{id}/` - Get product details
- `PUT /api/v1/products/{id}/` - Update product
- `DELETE /api/v1/products/{id}/` - Delete product
- `GET /api/v1/products/search/?q=` - Search products
- `GET /api/v1/products/stats/` - Product statistics
- `POST /api/v1/products/bulk-price-update/` - Bulk price updates

#### AI Services API

- `GET /api/v1/ai/search/?q=` - Semantic search
- `GET /api/v1/ai/insights/` - AI-powered insights
- `GET /api/v1/ai/search-analytics/` - Search analytics
- `POST /api/v1/ai/refresh-embeddings/` - Refresh AI embeddings

#### Webhooks API

- `POST /api/v1/webhooks/shopify/` - Shopify webhook handler
- `POST /api/v1/webhooks/inventory-update/` - Direct inventory updates
- `GET /api/v1/webhooks/events/` - List webhook events
- `POST /api/v1/webhooks/events/{id}/retry/` - Retry failed webhook

### Request/Response Examples

#### Create Product

```bash
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic <credentials>" \
  -d '{
    "name": "iPhone 15",
    "sku": "IP15-128",
    "price": 899.99,
    "inventory_quantity": 50,
    "description": "Latest iPhone model"
  }'
```

#### Semantic Search

```bash
curl "http://localhost:8000/api/v1/ai/search/?q=smartphone" \
  -H "Authorization: Basic <credentials>"
```

#### Shopify Webhook (for testing)

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/inventory-update/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "IP15-128",
    "available": 45,
    "inventory_item_id": "12345",
    "location_id": "67890"
  }'
```

### Filtering & Search Parameters

#### Product Filtering

- `GET /api/v1/products/?name=iPhone` - Filter by name
- `GET /api/v1/products/?price_min=100&price_max=1000` - Price range
- `GET /api/v1/products/?is_low_stock=true` - Low stock items
- `GET /api/v1/products/?ordering=-last_updated` - Sort by update time

## 🏗️ Architecture

### System Components

```plaintext
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django API    │    │     Celery      │    │      Redis      │
│                 │    │   (Background   │    │   (Cache &      │
│ - REST Endpoints │    │     Tasks)      │    │    Message      │
│ - Admin Panel    │    │                 │    │     Broker)     │
│ - Authentication │    └─────────────────┘    └─────────────────┘
└─────────────────┘              │                      │
         │                       │                      │
         ▼                       ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Database     │    │   AI Services   │    │    Webhooks     │
│                 │    │                 │    │                 │
│ - Products       │    │ - Semantic      │    │ - Shopify       │
│ - Inventory      │    │   Search        │    │   Integration   │
│ - Webhook Logs   │    │ - Embeddings    │    │ - Event         │
│ - Task History   │    │ - Insights      │    │   Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **API Requests** → Django views → Business logic → Database
2. **Shopify Webhooks** → Webhook processor → Celery tasks → Database updates
3. **Background Tasks** → Celery workers → Data processing → Email reports
4. **AI Search** → Embedding generation → Similarity matching → Ranked results

### Key Design Patterns

- **Repository Pattern**: Service classes for business logic
- **Observer Pattern**: Webhook event processing
- **Strategy Pattern**: Multiple search algorithms
- **Chain of Responsibility**: Celery task chains

## 🔧 Development Setup

### Local Development (Without Docker)

1. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Setup environment**

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run services**

   ```bash
   # Terminal 1: Django
   python manage.py runserver

   # Terminal 2: Celery Worker
   celery -A shopify_backend worker -l info

   # Terminal 3: Celery Beat (scheduler)
   celery -A shopify_backend beat -l info

   # Terminal 4: Redis
   redis-server
   ```

### Environment Variables

Create a `.env` file:

```plaintext
# Django Settings
SECRET_KEY=your-super-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Redis/Celery
REDIS_URL=redis://localhost:6379/0

# Shopify Integration
SHOPIFY_WEBHOOK_SECRET=your-shopify-webhook-secret

# AI Services
EMBEDDING_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
AI_CACHE_TIMEOUT=86400

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=admin@shopifybackend.com
```

## 🚀 Production Deployment

### Production Environment Variables

```plaintext
# Security
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://user:password@db:5432/shopify_backend

# Redis
REDIS_URL=redis://redis:6379/0

# Email (Production SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
```

## 🧪 Testing

### Run All Tests

```bash
# In Docker
docker-compose exec web python test_system.py

# Locally
python test_system.py
```

### Manual Testing Scripts

#### Test CSV Import

```python
from tasks.tasks import import_csv_data
result = import_csv_data.delay()
print(result.get())
```

#### Test AI Search

```python
from ai_services.services import AISearchService
ai_search = AISearchService()
results = ai_search.semantic_search("mobile phone", limit=5)
print([p.name for p in results])
```

#### Test Webhook Processing

```python
from webhooks.models import WebhookEvent
from webhooks.services import WebhookProcessor

webhook = WebhookEvent.objects.create(
    event_type='inventory_update',
    payload={'sku': 'IP14-128', 'available': 30},
    source='shopify'
)

processor = WebhookProcessor()
result = processor.process_webhook(webhook)
print(result)
```

## 📊 Monitoring & Logging

### Log Files

- `django.log`: General application logs
- Docker logs: `docker-compose logs -f web`

### Health Checks

```bash
# API Health
curl http://localhost:8000/api/v1/products/stats/

# Celery Health
docker-compose exec web celery -A shopify_backend inspect active

# Redis Health
docker-compose exec redis redis-cli ping
```

### Performance Monitoring

- Database query optimization with Django Debug Toolbar
- Celery task monitoring with Flower
- AI embedding cache hit rates

## 🔒 Security Best Practices

### API Security

- Authentication required for all endpoints
- Group-based permissions (API Users group)
- Rate limiting (implement django-ratelimit for production)
- CORS properly configured

### Webhook Security

- Webhook signature verification
- IP whitelisting (implement for production)
- Request size limits

### Data Security

- Database query parameterization (Django ORM)
- Input validation with DRF serializers
- SQL injection prevention
- XSS protection with Django templates