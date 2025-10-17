# CAMB.AI KVStore - Multi-Tenant Distributed Key-Value Store

Production-grade multi-tenant key-value store with FastAPI, Redis, Huey, and Kubernetes support. Built for horizontal scalability and complete tenant isolation.

## Features

- **Multi-tenant architecture** with complete data isolation using UUID-based tenant IDs
- **JWT-based authentication** with access tokens (30 min) and refresh tokens (7 days)
- **CRUD operations** with TTL support, versioning, and tag-based filtering
- **Background tasks** for TTL cleanup and audit logging using Huey
- **Prometheus metrics** and comprehensive health checks
- **Horizontal scalability** - capable of handling 10k+ req/s
- **Redis pipelining** for atomic operations and reduced round trips
- **Kubernetes-ready** with deployment configs, HPA, and monitoring

## Tech Stack

- **FastAPI** 0.109.0 - Modern async web framework
- **Redis** 7.2 - Primary data store and task queue
- **Huey** 2.5.0 - Background task processing
- **Python** 3.11 - Runtime
- **Docker** & **Kubernetes** - Containerization and orchestration
- **Prometheus** - Metrics and monitoring

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd camb-kvstore

# Setup environment
cp .env.example .env
# Edit .env and set SECRET_KEY (minimum 32 characters)

# Start all services (Redis, Redis-Huey, FastAPI app, Huey worker)
docker-compose up --build -d

# Verify health
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/docs
```

### Local Development

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY (minimum 32 characters)

# Run locally
uvicorn app.main:app --reload
```

## API Documentation

**Base URL**: `http://localhost:8000`

**Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)

**ReDoc**: `http://localhost:8000/redoc`

### Authentication Endpoints

#### Register User
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}

# Response includes tenant_id and tokens
{
  "tenant_id": "abc-123-def-456",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePass123"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Get Current User
```bash
GET /api/v1/auth/me
Authorization: Bearer {access_token}

# Response
{
  "username": "john_doe",
  "email": "john@example.com",
  "tenant_id": "abc-123-def-456",
  "is_active": true
}
```

#### Refresh Token
```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "{refresh_token}"
}

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Key-Value Operations

#### Create Key
```bash
POST /api/v1/kv
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "key": "user:123:profile",
  "value": "John Doe",
  "ttl": 3600,
  "tags": {"category": "user", "type": "profile"}
}

# Response
{
  "key": "user:123:profile",
  "value": "John Doe",
  "metadata": {
    "version": 1,
    "ttl": 3600,
    "tags": {"category": "user", "type": "profile"},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:00:00Z"
  }
}
```

#### Get Key
```bash
GET /api/v1/kv/{key}
Authorization: Bearer {access_token}

# Response includes value and metadata
{
  "key": "user:123:profile",
  "value": "John Doe",
  "metadata": {
    "version": 1,
    "ttl": 3600,
    "tags": {"category": "user", "type": "profile"},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:00:00Z"
  }
}
```

#### Update Key
```bash
PUT /api/v1/kv/{key}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "value": "Jane Doe",
  "ttl": 7200,
  "tags": {"category": "user", "type": "profile"}
}

# Version is automatically incremented
```

#### Delete Key
```bash
DELETE /api/v1/kv/{key}
Authorization: Bearer {access_token}

# Response
{
  "message": "Key deleted successfully"
}
```

#### List Keys (Paginated)
```bash
GET /api/v1/kv?page=1&page_size=20
Authorization: Bearer {access_token}

# Optional filters
GET /api/v1/kv?page=1&page_size=20&tag_filter=category:user
```

#### Batch Operations
```bash
POST /api/v1/kv/batch
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "items": [
    {"key": "key1", "value": "value1", "ttl": 3600},
    {"key": "key2", "value": "value2", "ttl": 3600}
  ]
}
```

#### Check Key Existence
```bash
GET /api/v1/kv/{key}/exists
Authorization: Bearer {access_token}

# Response
{
  "exists": true
}
```

#### Get TTL
```bash
GET /api/v1/kv/{key}/ttl
Authorization: Bearer {access_token}

# Response (seconds remaining)
{
  "ttl": 2847
}
```

#### Get Statistics
```bash
GET /api/v1/kv/stats/count
Authorization: Bearer {access_token}

# Response
{
  "count": 42
}
```

## Architecture Overview

### Multi-Tenancy Model

The system implements strict tenant isolation using UUID-based tenant IDs. Every user receives a unique `tenant_id` upon registration, which is embedded in their JWT tokens. All Redis operations are automatically namespaced by tenant ID, ensuring complete data isolation.

**Redis Key Namespacing:**

```
kv:{tenant_id}:{key}                # Key-value data
kv:{tenant_id}:{key}:metadata       # Metadata (version, tags, timestamps)
tenant_keys:{tenant_id}             # Set of all keys for a tenant
user:{tenant_id}                    # User account data
username_index:{username}           # Username to tenant_id lookup
email_index:{email}                 # Email to tenant_id lookup
audit:{tenant_id}:{timestamp}       # Audit log entries
```

**Example:**
```
User A (tenant: abc-123)
  key: "profile" → stored as "kv:abc-123:profile"

User B (tenant: xyz-789)
  key: "profile" → stored as "kv:xyz-789:profile"
```

Users cannot access other tenants' data - all operations are scoped to their tenant namespace.

### Authentication Flow

1. User registers via `/api/v1/auth/register` → receives unique `tenant_id` (UUID)
2. User logs in via `/api/v1/auth/login` → receives JWT access token (30 min) and refresh token (7 days)
3. Access token contains `tenant_id` in the `sub` claim
4. All authenticated requests extract `tenant_id` from token via dependency injection
5. Services use `tenant_id` to namespace all Redis operations

### Core Services Layer

The application follows a clean architecture with separate service layers:

**UserService** (`app/services/user_service.py`)
- Manages user CRUD operations
- Indexed lookups by username and email
- Password hashing and validation

**AuthService** (`app/services/auth_service.py`)
- User registration and login
- JWT token generation and verification
- Password validation against security requirements
- Refresh token handling

**KVStoreService** (`app/services/kvstore_service.py`)
- Core key-value operations with tenant namespacing
- All methods accept `tenant_id` as first parameter
- Features:
  - CRUD operations with TTL support
  - Automatic versioning (incremented on update)
  - Tag-based filtering
  - Batch operations
  - Metadata management (version, tags, timestamps)
  - Redis pipelining for atomic operations

### Dependency Injection Pattern

All services are instantiated via FastAPI dependencies (see `app/api/deps.py`):

```python
from app.api.deps import (
    get_redis,                    # Redis client
    get_kvstore_service,          # KVStore service
    get_current_active_user,      # User from JWT
    get_tenant_id                 # Tenant ID from JWT
)

@router.post("/kv")
async def create_key(
    request: CreateKeyRequest,
    tenant_id: str = Depends(get_tenant_id),
    kvstore_service: KVStoreService = Depends(get_kvstore_service)
):
    # tenant_id automatically extracted from JWT
    return await kvstore_service.create_key(tenant_id, request.key, request.value)
```

This pattern ensures:
- Services receive the correct Redis client
- User context is available throughout request lifecycle
- Clean separation of concerns
- Easy testing with mocked dependencies

### Background Tasks (Huey)

Background tasks use a separate Redis instance (redis-huey) for queue management:

**TTL Cleanup Task** (`app/tasks/ttl_cleanup.py`)
- Runs every 5 minutes
- Removes expired keys and their metadata
- Iterates through all tenant key sets
- Prevents memory bloat from expired keys

**Audit Logging Task** (`app/tasks/audit_logging.py`)
- Asynchronous logging of all KV operations
- Triggered by service layer after successful operations
- Stores operation type, key, timestamp, and metadata

**Huey Configuration** (`app/tasks/huey_config.py`)
- `immediate=True` in development (synchronous execution for testing)
- `immediate=False` in production (async queue processing)
- Separate Redis instance to avoid blocking primary data operations

### API Structure

```
app/api/v1/
├── __init__.py         # Aggregates all routers
├── auth.py             # /auth/* endpoints (register, login, refresh, me)
├── kvstore.py          # /kv/* endpoints (CRUD, batch, stats, exists, ttl)
└── health.py           # /health/* endpoints (liveness, readiness)
```

All endpoints are prefixed with `/api/v1` (configurable via `API_V1_PREFIX` in config).

### Data Flow

```
Client Request
    ↓
JWT Validation → Extract tenant_id
    ↓
FastAPI Endpoint (with dependencies)
    ↓
Service Layer (tenant-scoped operations)
    ↓
Redis (pipelined operations)
    ↓
Background Tasks (async via Huey)
    ↓
Redis Queue (redis-huey)
```

## Project Structure

```
camb-kvstore/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application entry point
│   ├── config.py                   # Configuration management (Pydantic)
│   ├── dependencies.py             # FastAPI dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py             # JWT handling, password hashing
│   │   ├── redis_client.py         # Redis connection pooling
│   │   └── custom_exceptions.py   # Custom exception classes
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                 # User data models
│   │   ├── kvstore.py              # KV store data models
│   │   └── token.py                # Token data models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py                 # User Pydantic schemas
│   │   ├── kvstore.py              # KV store Pydantic schemas
│   │   └── token.py                # Token request/response schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py             # Authentication endpoints
│   │       ├── kvstore.py          # KV store endpoints
│   │       └── health.py           # Health check endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py         # User business logic
│   │   ├── auth_service.py         # Auth business logic
│   │   └── kvstore_service.py      # KV store business logic
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── huey_config.py          # Huey task queue config
│   │   ├── ttl_cleanup.py          # TTL cleanup periodic task
│   │   └── audit_logging.py        # Audit logging task
│   └── utils/
│       ├── __init__.py
│       ├── logger.py               # Structured JSON logging
│       └── metrics.py              # Prometheus metrics
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Test fixtures and setup
│   ├── test_auth.py                # Authentication tests
│   ├── test_kvstore.py             # KV store operation tests
│   └── test_tasks.py               # Background task tests
├── kubernetes/
│   ├── namespace.yaml              # K8s namespace
│   ├── configmap.yaml              # Non-sensitive config
│   ├── secret.yaml                 # Sensitive data (base64)
│   ├── ingress.yaml                # Ingress configuration
│   ├── app/
│   │   ├── app-deployment.yaml     # FastAPI app deployment
│   │   ├── app-service.yaml        # K8s service
│   │   ├── hpa.yaml                # Horizontal Pod Autoscaler
│   │   └── huey-deployment.yaml    # Huey worker deployment
│   └── redis/
│       ├── redis-deployment.yaml   # Redis master deployment
│       ├── redis-service.yaml      # Redis service
│       ├── redis-pvc.yaml          # Persistent volume claim
│       └── redis-replica-deployment.yaml  # Redis replica
├── docker-compose.yml              # Local development setup
├── Dockerfile                      # FastAPI app container image
├── Dockerfile.huey                 # Huey worker container image
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore rules
├── deploy-kubernetes.sh            # Kubernetes deployment script
├── verify-kubernetes.sh            # Kubernetes verification script
└── README.md                       # This file
```

## Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```env
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

# Security (REQUIRED - minimum 32 characters)
SECRET_KEY=your-secret-key-at-least-32-characters-long

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (Primary)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

# Redis (Huey Queue)
REDIS_HUEY_HOST=localhost
REDIS_HUEY_PORT=6380
REDIS_HUEY_DB=0

# KV Store Limits
DEFAULT_TTL=3600
MAX_KEY_SIZE=256
MAX_VALUE_SIZE=2097152

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=8000
```

### Configuration Management

All configuration is centralized in `app/config.py` using Pydantic Settings:

- Type validation and conversion
- Environment variable loading from `.env` file
- Default values for optional settings
- Separate Redis configs for data and task queue
- Configurable token expiration times

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
pytest tests/test_kvstore.py -v
pytest tests/test_tasks.py -v

# Run specific test function
pytest tests/test_auth.py::test_register_user -v
pytest tests/test_kvstore.py::test_create_key -v
```

### Quick Manual Testing

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test1234"
  }'

# Save the access_token from response

# 2. Create a key
curl -X POST http://localhost:8000/api/v1/kv \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "mykey",
    "value": "myvalue",
    "ttl": 3600,
    "tags": {"type": "test"}
  }'

# 3. Get the key
curl -X GET http://localhost:8000/api/v1/kv/mykey \
  -H "Authorization: Bearer {access_token}"

# 4. List all keys
curl -X GET "http://localhost:8000/api/v1/kv?page=1&page_size=20" \
  -H "Authorization: Bearer {access_token}"

# 5. Delete the key
curl -X DELETE http://localhost:8000/api/v1/kv/mykey \
  -H "Authorization: Bearer {access_token}"
```

### Debugging Redis Operations

```bash
# Connect to Redis container
docker exec -it camb-redis redis-cli

# View all keys for a tenant (replace {tenant_id} with actual UUID)
SMEMBERS tenant_keys:{tenant_id}

# Get key value and metadata
GET kv:{tenant_id}:{key}
GET kv:{tenant_id}:{key}:metadata

# Check TTL (seconds remaining)
TTL kv:{tenant_id}:{key}

# View all keys (development only - avoid in production)
KEYS *

# Check Redis memory usage
INFO memory

# Monitor commands in real-time
MONITOR
```

## Docker Deployment

### Development with Docker Compose

```bash
# Start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Scale the application (multiple instances)
docker-compose up --scale app=3

# View logs
docker-compose logs -f app
docker-compose logs -f huey
docker-compose logs -f redis

# Stop services
docker-compose down

# Clean restart (removes volumes)
docker-compose down -v
docker-compose up --build

# Execute commands in container
docker-compose exec app bash
docker-compose exec redis redis-cli
```

### Services in Docker Compose

- **app** - FastAPI application (port 8000)
- **huey** - Huey worker for background tasks
- **redis** - Primary Redis instance (port 6379)
- **redis-huey** - Redis instance for Huey queue (port 6380)

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (minikube, kind, or cloud provider)
- kubectl configured
- Container registry (Docker Hub, GCR, ECR, etc.)

### Build and Push Image

```bash
# Build Docker image
docker build -t your-registry/camb-kvstore:latest .

# Push to registry
docker push your-registry/camb-kvstore:latest

# Update image in kubernetes/app/deployment.yaml
# Change: image: your-registry/camb-kvstore:latest
```

### Deploy to Kubernetes

```bash
# Create namespace and deploy all resources
kubectl apply -f kubernetes/

# Check deployment status
kubectl get all -n camb-kvstore

# Check pods
kubectl get pods -n camb-kvstore
kubectl describe pod <pod-name> -n camb-kvstore

# Check services
kubectl get services -n camb-kvstore

# Check persistent volumes
kubectl get pvc -n camb-kvstore
```

### Verify Deployment

```bash
# Check pod logs
kubectl logs -f deployment/camb-kvstore-app -n camb-kvstore
kubectl logs -f deployment/camb-kvstore-huey -n camb-kvstore

# Check Redis master
kubectl logs -f deployment/redis-master -n camb-kvstore

# Port forward to access locally
kubectl port-forward -n camb-kvstore svc/camb-kvstore-service 8000:8000

# Test API
curl http://localhost:8000/health
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/camb-kvstore-app \
  camb-kvstore=your-registry/camb-kvstore:v2.0 \
  -n camb-kvstore

# Check rollout status
kubectl rollout status deployment/camb-kvstore-app -n camb-kvstore

# View rollout history
kubectl rollout history deployment/camb-kvstore-app -n camb-kvstore

# Rollback to previous version
kubectl rollout undo deployment/camb-kvstore-app -n camb-kvstore
```

### Clean Up

```bash
# Delete all resources
kubectl delete -f kubernetes/

# Or delete namespace (removes everything)
kubectl delete namespace camb-kvstore
```

## Monitoring and Observability

### Prometheus Metrics

When `ENABLE_METRICS=true`, metrics are exposed at `/metrics`:

```bash
# View metrics
curl http://localhost:8000/metrics
```

**Available Metrics:**

- `http_requests_total` - Total HTTP requests (labels: method, endpoint, status)
- `http_request_duration_seconds` - Request duration histogram
- `kvstore_operations_total` - KV operations (labels: operation, tenant, status)
- `background_tasks_total` - Background task executions (labels: task, status)
- `active_connections` - Current active connections (gauge)

### Health Checks

```bash
# Basic health check (no dependencies)
curl http://localhost:8000/health

# Detailed health check (includes Redis connectivity)
curl http://localhost:8000/api/v1/health

# Kubernetes liveness probe
curl http://localhost:8000/api/v1/health/live

# Kubernetes readiness probe
curl http://localhost:8000/api/v1/health/ready
```

### Logging

Structured JSON logging via `app/utils/logger.py`:

```json
{
  "timestamp": "2025-10-17T12:00:00Z",
  "level": "INFO",
  "message": "Key created",
  "tenant_id": "abc-123",
  "key": "user:123",
  "operation": "create"
}
```

**Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL (configure via `LOG_LEVEL` env var)

**View Logs:**
```bash
# Docker Compose
docker-compose logs -f app

# Kubernetes
kubectl logs -f deployment/camb-kvstore-app -n camb-kvstore

# Follow logs for all pods
kubectl logs -f -l app=camb-kvstore -n camb-kvstore
```

## Security

### Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 digit (0-9)

Validation is enforced in `app/schemas/user.py` and `AuthService`.

### JWT Tokens

- **Access Token**: Short-lived (30 minutes default), contains tenant_id
- **Refresh Token**: Long-lived (7 days default), used to obtain new access tokens
- **Secret Key**: Must be at least 32 characters (set via `SECRET_KEY` env var)

### Data Isolation

- Each tenant's data is completely isolated using UUID-based namespacing
- Redis keys are prefixed with tenant_id
- Services validate tenant_id from JWT before every operation
- No shared data structures between tenants

### Best Practices

- Use strong SECRET_KEY (minimum 32 random characters)
- Enable HTTPS in production (configure via Ingress)
- Rotate JWT secrets periodically
- Use Redis password authentication in production
- Enable Redis TLS for encrypted connections
- Set appropriate CORS origins in production
- Use Kubernetes Secrets for sensitive data

## Performance and Scalability

### Horizontal Scaling

The application is stateless and can be scaled horizontally:

```bash
# Docker Compose
docker-compose up --scale app=5

# Kubernetes
kubectl scale deployment camb-kvstore-app --replicas=10 -n camb-kvstore
```

### Performance Characteristics

- **Throughput**: 10,000+ requests/second with proper Redis configuration
- **Latency**: Sub-millisecond for cache hits (p95 < 5ms)
- **Concurrency**: Async FastAPI handles thousands of concurrent connections
- **Redis**: Connection pooling prevents connection exhaustion

### Optimization Tips

1. **Redis Configuration**:
   - Increase `REDIS_MAX_CONNECTIONS` for high concurrency
   - Enable Redis persistence (RDB/AOF) for durability
   - Use Redis clustering for horizontal scaling

2. **Application Tuning**:
   - Adjust uvicorn workers: `--workers 4`
   - Use gunicorn with uvicorn workers in production
   - Enable Redis pipelining for batch operations

3. **Kubernetes**:
   - Configure HPA for auto-scaling
   - Set appropriate resource requests/limits
   - Use Redis StatefulSet for persistence

## Troubleshooting

### Common Issues

#### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Test Redis connectivity
docker exec -it camb-redis redis-cli PING
```

#### JWT Token Invalid

- Verify `SECRET_KEY` is set and at least 32 characters
- Check token hasn't expired (default: 30 minutes)
- Use refresh token to obtain new access token
- Ensure token is sent in Authorization header: `Bearer {token}`

### Kubernetes Troubleshooting

```bash
# Pod not starting
kubectl describe pod <pod-name> -n camb-kvstore
kubectl logs <pod-name> -n camb-kvstore

# Check events
kubectl get events -n camb-kvstore --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n camb-kvstore

# Debug pod
kubectl exec -it <pod-name> -n camb-kvstore -- bash

# Check service endpoints
kubectl get endpoints -n camb-kvstore
```

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Redis](https://redis.io/) - In-memory data store
- [Huey](https://huey.readthedocs.io/) - Lightweight task queue
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Docker](https://www.docker.com/) - Containerization
- [Kubernetes](https://kubernetes.io/) - Container orchestration