from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
from app.core.redis_client import get_redis
from app.core.custom_exceptions import AuthenticationError
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.kvstore_service import KVStoreService
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


def get_user_service(redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> UserService:
    return UserService(redis_client)


def get_auth_service(user_service: Annotated[UserService, Depends(get_user_service)]) -> AuthService:
    return AuthService(user_service)


def get_kvstore_service(redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> KVStoreService:
    return KVStoreService(redis_client)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> User:
    """This dependency to get current authenticated user extracting from attached JWT token."""
    try:
        token = credentials.credentials
        user = auth_service.verify_token(token)
        return user
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """This dependency is to get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is inactive"
        )
    return current_user


def get_tenant_id(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> str:
    """This dependency is to extract tenant id from current user."""
    return current_user.tenant_id