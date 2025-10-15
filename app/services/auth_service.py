from typing import Optional, Tuple
from datetime import timedelta
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type
)
from app.core.custom_exceptions import AuthenticationError, ResourceAlreadyExistsError
from app.services.user_service import UserService
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication and authorization operations."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def register_user(self, user_data: UserCreate) -> User:
        """Register a new user and return tokens."""
        user = self.user_service.create_user(user_data)
        logger.info(f"User registered successfully: {user.username}")
        return user

    def authenticate_user(self, credentials: UserLogin) -> Tuple[User, Token]:
        """Authenticate user and return tokens."""
        user = self.user_service.get_user_by_username(credentials.username)

        if not user:
            logger.warning(f"Authentication failed: User not found - {credentials.username}")
            raise AuthenticationError(detail="Incorrect username or password")

        if not verify_password(credentials.password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password - {credentials.username}")
            raise AuthenticationError(detail="Incorrect username or password")

        if not user.is_active:
            logger.warning(f"Authentication failed: Inactive user - {credentials.username}")
            raise AuthenticationError(detail="User account is inactive")

        tokens = self._generate_tokens(user)

        logger.info(f"User authenticated successfully: {user.username}")
        return user, tokens

    def refresh_access_token(self, refresh_token: str) -> Token:
        """Generate new access token using refresh token."""
        payload = decode_token(refresh_token)
        verify_token_type(payload, "refresh")

        tenant_id = payload.get("sub")
        if not tenant_id:
            raise AuthenticationError(detail="Invalid refresh token")

        user = self.user_service.get_user_by_tenant_id(tenant_id)
        if not user:
            raise AuthenticationError(detail="User not found")

        if not user.is_active:
            raise AuthenticationError(detail="User account is inactive")

        tokens = self._generate_tokens(user)

        logger.info(f"Access token refreshed for user: {user.username}")
        return tokens

    def verify_token(self, token: str) -> User:
        """Verify access token and return user."""
        payload = decode_token(token)
        verify_token_type(payload, "access")

        tenant_id = payload.get("sub")
        if not tenant_id:
            raise AuthenticationError(detail="Invalid token")

        user = self.user_service.get_user_by_tenant_id(tenant_id)
        if not user:
            raise AuthenticationError(detail="User not found")

        if not user.is_active:
            raise AuthenticationError(detail="User account is inactive")

        return user

    def _generate_tokens(self, user: User) -> Token:
        """Generate access and refresh tokens for user."""
        token_data = {
            "sub": user.tenant_id,
            "username": user.username
        }

        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        refresh_token = create_refresh_token(data=token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )