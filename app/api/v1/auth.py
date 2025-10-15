from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate
from app.schemas.token import Token, RefreshToken
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.api.deps import get_auth_service, get_user_service, get_current_active_user
from app.models.user import User
from app.core.custom_exceptions import (
    AuthenticationError,
    ResourceAlreadyExistsError,
    ValidationError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password"
)
async def register(
        user_data: UserCreate,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Register a new user (tenant).

    Creates a new user account and returns authentication tokens.
    Each user gets a unique tenant_id for data isolation.
    """
    try:
        user = auth_service.register_user(user_data)
        return {
            "user": UserResponse(
                tenant_id=user.tenant_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            ),
        }
    except ResourceAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with username and password"
)
async def login(
        credentials: UserLogin,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Authenticate user and return tokens."""
    try:
        user, tokens = auth_service.authenticate_user(credentials)

        return {
            "user": UserResponse(
                tenant_id=user.tenant_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            ),
            "tokens": tokens
        }
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
        refresh_data: RefreshToken,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Refresh access token using a valid refresh token."""
    try:
        tokens = auth_service.refresh_access_token(refresh_data.refresh_token)
        return tokens
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get currently authenticated user information"
)
async def get_current_user_info(
        current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get current authenticated user information."""
    return UserResponse(
        tenant_id=current_user.tenant_id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user",
    description="Update currently authenticated user information"
)
async def update_current_user(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)],
        user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Update current authenticated user information."""
    try:
        updated_user = user_service.update_user(current_user.tenant_id, user_update)

        return UserResponse(
            tenant_id=updated_user.tenant_id,
            username=updated_user.username,
            email=updated_user.email,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at
        )
    except ResourceAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user",
    description="Delete currently authenticated user account and all associated data"
)
async def delete_current_user(
        current_user: Annotated[User, Depends(get_current_active_user)],
        user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Delete current authenticated user account."""
    user_service.delete_user(current_user.tenant_id)
    logger.info(f"User account deleted: {current_user.username}")
    return None