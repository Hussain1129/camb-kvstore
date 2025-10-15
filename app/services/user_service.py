import json
import uuid
from typing import Optional
from datetime import datetime
import redis
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from app.core.custom_exceptions import ResourceAlreadyExistsError, ResourceNotFoundError, ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user management operations."""

    USER_PREFIX = "user"
    USERNAME_INDEX = "username_index"
    EMAIL_INDEX = "email_index"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _get_user_key(self, tenant_id: str) -> str:
        """Generate Redis key for user data."""
        return f"{self.USER_PREFIX}:{tenant_id}"

    def _get_username_key(self, username: str) -> str:
        """Generate Redis key for username index."""
        return f"{self.USERNAME_INDEX}:{username}"

    def _get_email_key(self, email: str) -> str:
        """Generate Redis key for email index."""
        return f"{self.EMAIL_INDEX}:{email}"

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        if self.redis.exists(self._get_username_key(user_data.username)):
            raise ResourceAlreadyExistsError(detail=f"Username '{user_data.username}' already exists")

        if self.redis.exists(self._get_email_key(str(user_data.email))):
            raise ResourceAlreadyExistsError(detail=f"Email '{user_data.email}' already exists")

        tenant_id = str(uuid.uuid4())

        try:
            hashed_password = get_password_hash(user_data.password)
        except:
            raise ValidationError(detail="Invalid password, re-arranged it")

        user = User(
            tenant_id=tenant_id,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        pipeline = self.redis.pipeline()

        pipeline.set(self._get_user_key(tenant_id), json.dumps(user.to_dict()))
        pipeline.set(self._get_username_key(user.username), tenant_id)
        pipeline.set(self._get_email_key(str(user.email)), tenant_id)

        pipeline.execute()

        logger.info(f"User created successfully: {user_data.username} (tenant_id: {tenant_id})")
        return user

    def get_user_by_tenant_id(self, tenant_id: str) -> Optional[User]:
        """Get user by tenant ID."""
        user_data: str = self.redis.get(self._get_user_key(tenant_id))
        if not user_data:
            return None

        return User.from_dict(json.loads(user_data))

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        tenant_id = self.redis.get(self._get_username_key(username))
        if not tenant_id:
            return None

        return self.get_user_by_tenant_id(tenant_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        tenant_id = self.redis.get(self._get_email_key(email))
        if not tenant_id:
            return None

        return self.get_user_by_tenant_id(tenant_id)

    def update_user(self, tenant_id: str, user_update: UserUpdate) -> User:
        """Update user information."""
        user = self.get_user_by_tenant_id(tenant_id)
        if not user:
            raise ResourceNotFoundError(detail=f"User with tenant_id '{tenant_id}' not found")

        pipeline = self.redis.pipeline()

        if user_update.email and user_update.email != user.email:
            if self.redis.exists(self._get_email_key(str(user_update.email))):
                raise ResourceAlreadyExistsError(detail=f"Email '{user_update.email}' already exists")

            pipeline.delete(self._get_email_key(str(user.email)))
            pipeline.set(self._get_email_key(str(user_update.email)), tenant_id)
            user.email = user_update.email

        if user_update.password:
            user.hashed_password = get_password_hash(user_update.password)

        user.updated_at = datetime.utcnow()

        pipeline.set(self._get_user_key(tenant_id), json.dumps(user.to_dict()))
        pipeline.execute()

        logger.info(f"User updated successfully: {user.username} (tenant_id: {tenant_id})")
        return user

    def delete_user(self, tenant_id: str) -> bool:
        """Delete user and all associated data."""
        user = self.get_user_by_tenant_id(tenant_id)
        if not user:
            raise ResourceNotFoundError(detail=f"User with tenant_id '{tenant_id}' not found")

        pipeline = self.redis.pipeline()

        pipeline.delete(self._get_user_key(tenant_id))
        pipeline.delete(self._get_username_key(user.username))
        pipeline.delete(self._get_email_key(str(user.email)))

        kv_pattern = f"kv:{tenant_id}:*"
        for key in self.redis.scan_iter(match=kv_pattern):
            pipeline.delete(key)

        pipeline.execute()

        logger.info(f"User deleted successfully: {user.username} (tenant_id: {tenant_id})")
        return True

    def user_exists(self, tenant_id: str) -> bool:
        """Check if user exists."""
        return self.redis.exists(self._get_user_key(tenant_id)) > 0