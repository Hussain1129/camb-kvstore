from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for API errors."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationError(BaseAPIException):
    """Authentication failed exception."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(BaseAPIException):
    """Authorization failed exception."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ResourceNotFoundError(BaseAPIException):
    """Resource not found exception."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ResourceAlreadyExistsError(BaseAPIException):
    """Resource already exists exception."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT
        )


class ValidationError(BaseAPIException):
    """Validation error exception."""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class RateLimitError(BaseAPIException):
    """Rate limit exceeded exception."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class RedisConnectionError(BaseAPIException):
    """Redis connection error exception."""

    def __init__(self, detail: str = "Redis connection failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class KeyValueStoreError(BaseAPIException):
    """Generic KV store error exception."""

    def __init__(self, detail: str = "Key-value store operation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )