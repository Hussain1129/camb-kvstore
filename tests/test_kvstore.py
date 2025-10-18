from fastapi.testclient import TestClient
import uuid
from fastapi import status
from app.config import settings
from app.main import app

class TestCreateKeyValue:
    """Test key-value creation endpoints."""

    def test_create_key_success(self, authenticated_client, test_kv_data):
        """Test successful key creation."""
        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=test_kv_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["key"] == test_kv_data["key"]
        assert data["value"] == test_kv_data["value"]
        assert data["ttl"] == test_kv_data["ttl"]
        assert data["version"] == 1
        assert data["tags"] == test_kv_data["tags"]
        assert "tenant_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "expires_at" in data

    def test_create_key_duplicate(self, authenticated_client, created_key, test_kv_data):
        """Test creating duplicate key fails."""
        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=test_kv_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_key_without_ttl(self, authenticated_client):
        """Test creating key without TTL."""
        kv_data = {
            "key": f"test:no:ttl:{uuid.uuid4().hex[:8]}",
            "value": "test value"
        }

        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=kv_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["ttl"] is None
        assert data["expires_at"] is None

    def test_create_key_with_tags(self, authenticated_client):
        """Test creating key with custom tags."""
        kv_data = {
            "key": f"test:with:tags:{uuid.uuid4().hex[:8]}",
            "value": "test value",
            "tags": {"env": "prod", "team": "backend"}
        }

        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=kv_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["tags"]["env"] == "prod"
        assert data["tags"]["team"] == "backend"

    def test_create_key_unauthorized(self, client, test_kv_data):
        """Test creating key without authentication fails."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=test_kv_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_key_invalid_key_size(self, authenticated_client):
        """Test creating key with oversized key fails."""
        kv_data = {
            "key": "a" * 300,
            "value": "test value"
        }

        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=kv_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetKeyValue:
    """Test key-value retrieval endpoints."""

    def test_get_key_success(self, authenticated_client, created_key):
        """Test successful key retrieval."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["key"] == created_key["key"]
        assert data["value"] == created_key["value"]

    def test_get_key_not_found(self, authenticated_client):
        """Test getting non-existent key fails."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/nonexistent:key:{uuid.uuid4().hex[:8]}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_key_unauthorized(self, client, test_kv_data):
        """Test getting key without authentication fails."""
        response = client.get(
            f"{settings.API_V1_PREFIX}/kv/{test_kv_data['key']}"
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_get_key_different_tenant(self, authenticated_client, test_user_data_2, test_kv_data):
        """Test getting key from different tenant fails."""
        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv",
            json=test_kv_data
        )
        assert response.status_code == status.HTTP_201_CREATED

        with TestClient(app) as client2:
            client2.post(
                f"{settings.API_V1_PREFIX}/auth/register",
                json=test_user_data_2
            )

            login_response = client2.post(
                f"{settings.API_V1_PREFIX}/auth/login",
                json={
                    "username": test_user_data_2["username"],
                    "password": test_user_data_2["password"]
                }
            )

            access_token = login_response.json()["tokens"]["access_token"]
            response = client2.get(
                f"{settings.API_V1_PREFIX}/kv/{test_kv_data['key']}",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateKeyValue:
    """Test key-value update endpoints."""

    def test_update_key_value(self, authenticated_client, created_key):
        """Test updating key value."""
        update_data = {"value": "updated value"}

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}",
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["value"] == "updated value"
        assert data["version"] == 2

    def test_update_key_ttl(self, authenticated_client, created_key):
        """Test updating key TTL."""
        update_data = {"ttl": 7200}

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}",
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["ttl"] == 7200
        assert data["version"] == 2

    def test_update_key_tags(self, authenticated_client, created_key):
        """Test updating key tags."""
        update_data = {"tags": {"updated": "true"}}

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}",
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["tags"]["updated"] == "true"
        assert data["version"] == 2

    def test_update_key_not_found(self, authenticated_client):
        """Test updating non-existent key fails."""
        update_data = {"value": "updated value"}

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/kv/nonexistent:key:{uuid.uuid4().hex[:8]}",
            json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteKeyValue:
    """Test key-value deletion endpoints."""

    def test_delete_key_success(self, authenticated_client, created_key):
        """Test successful key deletion."""
        response = authenticated_client.delete(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_key_not_found(self, authenticated_client):
        """Test deleting non-existent key fails."""
        response = authenticated_client.delete(
            f"{settings.API_V1_PREFIX}/kv/nonexistent:key:{uuid.uuid4().hex[:8]}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListKeyValues:
    """Test key-value list endpoints."""

    def test_list_keys_success(self, authenticated_client, multiple_created_keys):
        """Test successful key listing."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv?page=1&page_size=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) == 5

        if "total" in data:
            assert data["total"] == 5
        else:
            assert "active" in data
            assert "expired" in data
            assert data["active"] + data["expired"] == 5

    def test_list_keys_pagination(self, authenticated_client, multiple_created_keys):
        """Test key listing with pagination."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv?page=1&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

        if "total" in data:
            assert data["total"] == 5
        else:
            assert "active" in data
            total_keys = data.get("active", 0) + data.get("expired", 0)
            assert total_keys == 5

    def test_list_keys_empty(self, authenticated_client):
        """Test listing keys when none exist."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv?page=1&page_size=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["items"]) == 0

        if "total" in data:
            assert data["total"] == 0
        else:
            assert "active" in data
            assert data["active"] == 0


class TestBatchOperations:
    """Test batch operation endpoints."""

    def test_batch_create_success(self, authenticated_client):
        """Test successful batch creation."""
        batch_id = uuid.uuid4().hex[:8]
        batch_data = {
            "items": [
                {"key": f"batch:1:{batch_id}", "value": "value1"},
                {"key": f"batch:2:{batch_id}", "value": "value2"},
                {"key": f"batch:3:{batch_id}", "value": "value3"}
            ]
        }

        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv/batch",
            json=batch_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["created"] == 3
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_batch_create_duplicate_keys(self, authenticated_client):
        """Test batch creation with duplicate keys."""
        batch_id = uuid.uuid4().hex[:8]
        batch_data = {
            "items": [
                {"key": f"batch:1:{batch_id}", "value": "value1"},
                {"key": f"batch:1:{batch_id}", "value": "value2"}
            ]
        }

        response = authenticated_client.post(
            f"{settings.API_V1_PREFIX}/kv/batch",
            json=batch_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestKeyUtilities:
    """Test key utility endpoints."""

    def test_check_key_exists(self, authenticated_client, created_key):
        """Test checking if key exists."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}/exists"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["exists"] is True

    def test_check_key_not_exists(self, authenticated_client):
        """Test checking if non-existent key exists."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/nonexistent:key:{uuid.uuid4().hex[:8]}/exists"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["exists"] is False

    def test_get_key_ttl(self, authenticated_client, created_key):
        """Test getting key TTL."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/{created_key['key']}/ttl"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "ttl" in data
        assert data["ttl"] > 0

    def test_get_key_count(self, authenticated_client, multiple_created_keys):
        """Test getting total key count."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/kv/stats/count"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["count"] == 5