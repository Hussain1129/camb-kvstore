import pytest
import redis
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.redis_client import redis_client


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
def test_user_data():
    """Fixture for test user data."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPass123"
    }


@pytest.fixture(scope="function")
def test_user_data_2():
    """Fixture for second test user data."""
    return {
        "username": "testuser2",
        "email": "testuser2@example.com",
        "password": "TestPass456"
    }


@pytest.fixture(scope="function")
def test_kv_data():
    """Fixture for test key-value data."""
    return {
        "key": "test:key:1",
        "value": "test value",
        "ttl": 3600,
        "tags": {"env": "test", "type": "string"}
    }


@pytest.fixture(scope="function")
def test_kv_data_2():
    """Fixture for second test key-value data."""
    return {
        "key": "test:key:2",
        "value": "another test value",
        "ttl": 7200,
        "tags": {"env": "test", "type": "string"}
    }


@pytest.fixture(scope="function")
def registered_user(client, test_user_data):
    """Fixture for registered user with tokens."""
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json=test_user_data
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="function")
def registered_user_2(client, test_user_data_2):
    """Fixture for second registered user with tokens."""
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json=test_user_data_2
    )
    assert response.status_code == 201
    return response.json()


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
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="function")
def multiple_created_keys(authenticated_client):
    """Fixture for multiple created key-value pairs."""
    keys = []
    for i in range(5):
        kv_data = {
            "key": f"test:key:{i}",
            "value": f"test value {i}",
            "ttl": 3600,
            "tags": {"index": str(i), "batch": "test"}
        }
        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=kv_data
        )
        assert response.status_code == 201
        keys.append(response.json())
    return keys


@pytest.fixture(autouse=True)
def reset_redis_between_tests(test_redis_client):
    """Automatically reset Redis between tests."""
    yield
    test_redis_client.flushdb()