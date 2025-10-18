import pytest
from fastapi.testclient import TestClient
import redis
import uuid
from httpx import AsyncClient
from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def test_settings():
    """Fixture for test settings."""
    return settings


@pytest.fixture(scope="session")
def test_redis_client():
    """Fixture for test Redis connection."""
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB + 1,
        decode_responses=True
    )

    yield client

    client.flushdb()
    client.close()


@pytest.fixture(scope="function")
def clean_redis(test_redis_client):
    """Fixture to clean Redis before each test."""
    test_redis_client.flushdb()
    yield
    test_redis_client.flushdb()


@pytest.fixture(scope="module")
def client():
    """Fixture for FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client():
    """Fixture for async FastAPI test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def test_user_data():
    """Fixture for test user data with unique identifier."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "password": "TestPass123"
    }


@pytest.fixture(scope="function")
def test_user_data_2():
    """Fixture for second test user data with unique identifier."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser2_{unique_id}",
        "email": f"testuser2_{unique_id}@example.com",
        "password": "TestPass456"
    }


@pytest.fixture(scope="function")
def test_kv_data():
    """Fixture for test key-value data with unique identifier."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "key": f"test:key:1:{unique_id}",
        "value": "test value",
        "ttl": 3600,
        "tags": {"env": "test", "type": "string", "unique_id": unique_id}
    }


@pytest.fixture(scope="function")
def test_kv_data_2():
    """Fixture for second test key-value data with unique identifier."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "key": f"test:key:2:{unique_id}",
        "value": "another test value",
        "ttl": 7200,
        "tags": {"env": "test", "type": "string", "unique_id": unique_id}
    }


@pytest.fixture(scope="function")
def registered_user(client, test_user_data):
    """Fixture for registered user with tokens."""
    register_response = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json=test_user_data
    )
    assert register_response.status_code == 201, f"Registration failed: {register_response.json()}"

    login_response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

    return login_response.json()


@pytest.fixture(scope="function")
def registered_user_2(client, test_user_data_2):
    """Fixture for second registered user with tokens."""
    register_response = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json=test_user_data_2
    )
    assert register_response.status_code == 201, f"Registration failed: {register_response.json()}"

    login_response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "username": test_user_data_2["username"],
            "password": test_user_data_2["password"]
        }
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

    return login_response.json()


@pytest.fixture(scope="function")
def auth_headers(registered_user):
    """Fixture for authentication headers."""
    access_token = registered_user["tokens"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def auth_headers_2(registered_user_2):
    """Fixture for second user authentication headers."""
    access_token = registered_user_2["tokens"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def authenticated_client(client, auth_headers):
    """Fixture for authenticated test client."""
    client.headers.update(auth_headers)
    yield client
    client.headers.clear()


@pytest.fixture(scope="function")
def created_key(authenticated_client, test_kv_data):
    """Fixture for created key-value pair."""
    response = authenticated_client.post(
        f"{settings.API_V1_PREFIX}/kv",
        json=test_kv_data
    )
    assert response.status_code == 201, f"Key creation failed: {response.json()}"
    return response.json()


@pytest.fixture(scope="function")
def multiple_created_keys(authenticated_client):
    """Fixture for multiple created key-value pairs with unique identifiers."""
    keys = []
    batch_id = uuid.uuid4().hex[:8]

    for i in range(5):
        kv_data = {
            "key": f"test:key:{i}:{batch_id}",
            "value": f"test value {i}",
            "ttl": 3600,
            "tags": {"index": str(i), "batch": batch_id, "batch_type": "test"}
        }
        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=kv_data
        )
        assert response.status_code == 201, f"Key creation failed: {response.json()}"
        keys.append(response.json())

    return keys


@pytest.fixture(autouse=True)
def reset_redis_between_tests(test_redis_client):
    """Automatically reset Redis between tests."""
    yield
    test_redis_client.flushdb()