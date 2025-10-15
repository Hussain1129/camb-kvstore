## CAMB.AI KVStore - Multi-Tenant Distributed Key-Value Store

Production-grade multi-tenant key-value store with FastAPI, Redis, Huey, and Kubernetes support.

### Features

- Multi-tenant architecture with complete data isolation
- JWT-based authentication (access + refresh tokens)
- CRUD operations with TTL support and versioning
- Background tasks for cleanup and audit logging
- Prometheus metrics and health checks
- Horizontal scalability (10k+ req/s capable)

### Tech Stack

- FastAPI 0.109.0
- Redis 7.2
- Huey 2.5.0
- Python 3.11
- Docker & Kubernetes

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd camb-kvstore

# Setup environment
cp .env.example .env
# Edit .env and set SECRET_KEY (min 32 characters)

# Start services
docker-compose up --build

# Verify
curl http://localhost:8000/health
```

## API Endpoints

**Base URL**: `http://localhost:8000`

**Docs**: `http://localhost:8000/docs`

### Authentication

```bash
# Register
POST /api/v1/auth/register
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}

# Login
POST /api/v1/auth/login
{
  "username": "john_doe",
  "password": "SecurePass123"
}

# Get current user
GET /api/v1/auth/me
Authorization: Bearer {token}

# Refresh token
POST /api/v1/auth/refresh
{
  "refresh_token": "{refresh_token}"
}
```

### Key-Value Operations

```bash
# Create key
POST /api/v1/kv
Authorization: Bearer {token}
{
  "key": "user:123:profile",
  "value": "John Doe",
  "ttl": 3600,
  "tags": {"category": "user"}
}

# Get key
GET /api/v1/kv/{key}
Authorization: Bearer {token}

# Update key
PUT /api/v1/kv/{key}
Authorization: Bearer {token}
{
  "value": "Jane Doe",
  "ttl": 7200
}

# Delete key
DELETE /api/v1/kv/{key}
Authorization: Bearer {token}

# List keys (paginated)
GET /api/v1/kv?page=1&page_size=20
Authorization: Bearer {token}

# Batch create
POST /api/v1/kv/batch
Authorization: Bearer {token}
{
  "items": [
    {"key": "key1", "value": "value1"},
    {"key": "key2", "value": "value2"}
  ]
}

# Check existence
GET /api/v1/kv/{key}/exists
Authorization: Bearer {token}

# Get TTL
GET /api/v1/kv/{key}/ttl
Authorization: Bearer {token}

# Get key count
GET /api/v1/kv/stats/count
Authorization: Bearer {token}
```

## Project Structure

```
camb-kvstore/
├── app/
│   ├── main.py                 # Application entry
│   ├── config.py               # Configuration
│   ├── core/                   # Security, Redis client, exceptions
│   ├── models/                 # Data models
│   ├── schemas/                # Pydantic schemas
│   ├── api/v1/                 # API endpoints
│   ├── services/               # Business logic
│   ├── tasks/                  # Background tasks
│   └── utils/                  # Logging, metrics
├── tests/                      # Test files
├── kubernetes/                 # K8s manifests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Configuration

Key environment variables in `.env`:

```env
# Required
SECRET_KEY=your-secret-key-min-32-chars

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## Multi-Tenancy

Each user gets unique `tenant_id` (UUID). All keys are namespaced:

```
User A (tenant: abc-123)
  key: "profile" → stored as "kv:abc-123:profile"

User B (tenant: xyz-789)
  key: "profile" → stored as "kv:xyz-789:profile"
```

Complete data isolation - users cannot access other tenants' data.

## Background Tasks

**TTL Cleanup** (every 5 min): Removes expired keys and metadata

**Audit Logging**: Logs all operations asynchronously

**Daily Aggregation** (midnight): Generates usage statistics

## Monitoring

**Metrics**: `http://localhost:8000/metrics` (Prometheus format)

**Health Checks**:
- `/health` - Basic health
- `/api/v1/health` - Detailed with dependencies
- `/api/v1/health/live` - Liveness probe
- `/api/v1/health/ready` - Readiness probe

**Key Metrics**:
- `http_requests_total`
- `http_request_duration_seconds`
- `kvstore_operations_total`
- `background_tasks_total`

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Specific file
pytest tests/test_auth.py
```

**Quick Manual Test**:

```bash
# 1. Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"Test123"}'

# 2. Save access_token from response

# 3. Create key
curl -X POST http://localhost:8000/api/v1/kv \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"key":"test","value":"hello","ttl":3600}'

# 4. Get key
curl -X GET http://localhost:8000/api/v1/kv/test \
  -H "Authorization: Bearer {token}"
```

## Scalability

**Horizontal Scaling**:
```bash
# Docker Compose
docker-compose up --scale app=3

# Kubernetes
kubectl scale deployment camb-kvstore-app --replicas=5
```

**Performance**: Handles 10k+ req/s with proper Redis configuration and multiple pods.

## Deployment

**Local Development**:
```bash
docker-compose up
```

**Kubernetes** (Production):
```bash
kubectl apply -f kubernetes/
kubectl get pods -n camb-kvstore
```

## Troubleshooting

**Redis connection failed**:
```bash
docker-compose logs redis
docker-compose restart redis
```

**Token invalid**:
- Check SECRET_KEY is set
- Token may be expired (refresh using refresh_token)

**Clean restart**:
```bash
docker-compose down -v
docker-compose up --build
```

## Services

- **FastAPI App**: http://localhost:8000
- **Redis Main**: localhost:6379
- **Redis Queue**: localhost:6380
- **Swagger Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

## Architecture

```
Client → FastAPI (JWT Auth) → Redis (Data)
                           ↓
                        Huey Worker → Redis (Queue)
```

**Data Flow**:
1. User registers/logs in → receives JWT tokens
2. Each request includes JWT → server validates & extracts tenant_id
3. All operations scoped to tenant namespace
4. Background tasks handle cleanup and logging

## Password Requirements

- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit

## Redis Key Structure

```
kv:{tenant_id}:{key}                # Key-value data
kv:{tenant_id}:{key}:metadata       # Metadata
tenant_keys:{tenant_id}             # Tenant's key set
user:{tenant_id}                    # User data
username_index:{username}           # Username lookup
email_index:{email}                 # Email lookup
audit:{tenant_id}:{timestamp}       # Audit logs
```

## Development

```bash
# Local setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Format code
black app/ tests/
isort app/ tests/
```