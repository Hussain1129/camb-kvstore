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


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create new user account with details of username, email, and password"
)
async def register(
        user_data: UserCreate,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    try:
        user = auth_service.register_user(user_data)
        return {"user": _user_response(user)}
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
    try:
        user, tokens = auth_service.authenticate_user(credentials)
        return {"user": _user_response(user), "tokens": tokens}
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token by taking refresh token"
)
async def refresh_token(
        refresh_data: RefreshToken,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
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
    return _user_response(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user",
    description="Update the currently authenticated user information"
)
async def update_current_user(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)],
        user_service: Annotated[UserService, Depends(get_user_service)]
):
    try:
        updated_user = user_service.update_user(current_user.tenant_id, user_update)
        return _user_response(updated_user)
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
    user_service.delete_user(current_user.tenant_id)
    logger.info(f"Account deleted: {current_user.username}")
    return None