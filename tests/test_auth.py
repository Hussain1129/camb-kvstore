import pytest
from fastapi import status
from app.config import settings


class TestUserRegistration:
    """Test user registration endpoints."""

    def test_register_user_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "user" in data
        assert "tokens" in data
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["email"] == test_user_data["email"]
        assert "tenant_id" in data["user"]
        assert data["user"]["is_active"] is True

        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"
        assert data["tokens"]["expires_in"] > 0

    def test_register_user_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username fails."""
        client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    def test_register_user_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email fails."""
        client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        test_user_data["username"] = "different_username"
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    def test_register_user_invalid_password(self, client, test_user_data):
        """Test registration with invalid password fails."""
        test_user_data["password"] = "weak"

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_invalid_email(self, client, test_user_data):
        """Test registration with invalid email fails."""
        test_user_data["email"] = "invalid-email"

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_short_username(self, client, test_user_data):
        """Test registration with short username fails."""
        test_user_data["username"] = "ab"

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json=test_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login endpoints."""

    def test_login_success(self, client, test_user_data, registered_user):
        """Test successful user login."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "user" in data
        assert "tokens" in data
        assert data["user"]["username"] == test_user_data["username"]
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_login_invalid_username(self, client, test_user_data):
        """Test login with invalid username fails."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "nonexistent",
                "password": test_user_data["password"]
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_password(self, client, test_user_data, registered_user):
        """Test login with invalid password fails."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": test_user_data["username"],
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test token refresh endpoints."""

    def test_refresh_token_success(self, client, registered_user):
        """Test successful token refresh."""
        refresh_token = registered_user["tokens"]["refresh_token"]

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token fails."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCurrentUser:
    """Test current user endpoints."""

    def test_get_current_user_success(self, authenticated_client, test_user_data):
        """Test getting current user information."""
        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/auth/me"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "tenant_id" in data
        assert data["is_active"] is True

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication fails."""
        response = client.get(
            f"{settings.API_V1_PREFIX}/auth/me"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_current_user_email(self, authenticated_client, test_user_data):
        """Test updating current user email."""
        new_email = "newemail@example.com"

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/auth/me",
            json={"email": new_email}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["email"] == new_email

    def test_update_current_user_password(self, authenticated_client, test_user_data):
        """Test updating current user password."""
        new_password = "NewSecurePass123"

        response = authenticated_client.put(
            f"{settings.API_V1_PREFIX}/auth/me",
            json={"password": new_password}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_delete_current_user(self, authenticated_client):
        """Test deleting current user."""
        response = authenticated_client.delete(
            f"{settings.API_V1_PREFIX}/auth/me"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = authenticated_client.get(
            f"{settings.API_V1_PREFIX}/auth/me"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED