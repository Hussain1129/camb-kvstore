# CAMB.AI KVStore

Multi-tenant key-value store built with FastAPI, Redis, and Huey. Designed for horizontal scalability with complete tenant isolation.

## Features

- Multi-tenant architecture with UUID-based tenant IDs
- JWT authentication (access + refresh tokens)
- CRUD operations with TTL support and versioning
- Background tasks for TTL cleanup and audit logging
- Kubernetes deployment configs

## Tech Stack

- FastAPI 0.109.0
- Redis 7.2
- Huey 2.5.0
- Python 3.11
- Docker & Kubernetes

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
# Edit .env and set SECRET_KEY (min 32 chars)

docker-compose up --build

# Verify
curl http://localhost:8000/health
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set SECRET_KEY in .env

uvicorn app.main:app --reload
```

## API Usage

**Docs**: http://localhost:8000/docs

### Register & Login

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "Test1234"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "Test1234"}'

# Save the access_token from response
```

### Key-Value Operations

```bash
# Create
curl -X POST http://localhost:8000/api/v1/kv \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"key": "user:123", "value": "John Doe", "ttl": 3600}'

# Get
curl http://localhost:8000/api/v1/kv/user:123 \
  -H "Authorization: Bearer {access_token}"

# Update
curl -X PUT http://localhost:8000/api/v1/kv/user:123 \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"value": "Jane Doe"}'

# Delete
curl -X DELETE http://localhost:8000/api/v1/kv/user:123 \
  -H "Authorization: Bearer {access_token}"

# List (paginated)
curl "http://localhost:8000/api/v1/kv?page=1&page_size=20" \
  -H "Authorization: Bearer {access_token}"
```

## Architecture

### Multi-Tenancy

Each user gets a unique `tenant_id` (UUID) on registration. All Redis keys are namespaced:

```
kv:{tenant_id}:{key}                # actual data
kv:{tenant_id}:{key}:metadata       # metadata (version, tags, timestamps)
tenant_keys:{tenant_id}             # set of all keys for tenant
user:{tenant_id}                    # user data
```

### Authentication Flow

1. User registers → gets `tenant_id`
2. Login → receive JWT access token (30min) + refresh token (7 days)
3. Token contains `tenant_id` in sub claim
4. All requests extract `tenant_id` from JWT
5. Services automatically namespace operations by tenant

### Services

- **UserService**: User CRUD with indexed lookups
- **AuthService**: Registration, login, token management
- **KVStoreService**: Core KV operations with tenant isolation

All services use dependency injection via FastAPI's Depends.

### Background Tasks

- **TTL Cleanup**: Runs every 5 minutes, removes expired keys
- **Audit Logging**: Async logging of all operations

Tasks run on separate Redis instance (redis-huey) to avoid blocking.

## Testing

```bash
pytest
pytest -v
pytest tests/test_kvstore.py -v     # run particular file
```

## Docker

```bash
# Start all services by making build first
docker-compose up -d --build

# If have build, start all services in docker 
docker-compose up -d

# View and check logs -- for detail logging
docker-compose logs -f app

# remove all service include their columns and then Clean restart by creating new build
docker-compose down -v && docker-compose up --build
```

Services: app (FastAPI), huey (worker), redis, redis-huey

## Kubernetes

```bash
# Build and push image
docker build -t your-registry/camb-kvstore:latest .
docker push your-registry/camb-kvstore:latest

# Deploy
kubectl apply -f kubernetes/

# Check status
kubectl get all -n camb-kvstore

# View logs
kubectl logs -f deployment/camb-kvstore-app -n camb-kvstore

# Port forward
kubectl port-forward -n camb-kvstore svc/camb-kvstore-service 8000:8000
```

## Configuration

Key environment variables:

```
SECRET_KEY=your-secret-key-at-least-32-chars  # REQUIRED
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_HOST=localhost
REDIS_PORT=6379
```

See `.env.example` for full list.

## Project Structure

```
app/
├── api/v1/          # API endpoints
├── core/            # Security, exceptions, Redis client
├── models/          # Data models
├── schemas/         # Pydantic schemas
├── services/        # Business logic
├── tasks/           # Huey background tasks
└── utils/           # Logging
```

## Security

- Passwords: min 8 chars, 1 uppercase, 1 lowercase, 1 digit
- JWT tokens with configurable expiration
- Complete tenant isolation via UUID namespacing
- Use strong SECRET_KEY (32+ random chars)

## Performance

- 10k+ req/s with proper Redis config
- Redis pipelining for atomic operations
- Connection pooling

TODO: Add rate limiting

## Monitoring

Health checks:
- `/health` - Basic health
- `/api/v1/health/ready` - Readiness probe
- `/api/v1/health/live` - Liveness probe

## Debugging

```bash
# Redis CLI
docker exec -it camb-redis redis-cli

# View tenant keys
SMEMBERS tenant_keys:{tenant_id}

# Check key
GET kv:{tenant_id}:{key}
TTL kv:{tenant_id}:{key}
```
