import redis
from redis.connection import ConnectionPool
from typing import Optional
from app.config import settings
from app.core.custom_exceptions import RedisConnectionError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client manager with connection pooling."""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
                encoding='utf-8'
            )
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            self._client.ping()
            logger.info("Redis connection established successfully")

        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise RedisConnectionError(detail=f"Failed to connect to Redis: {str(e)}")

    def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            self._client.close()
            logger.info("Redis connection closed")

        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool disconnected")

    def get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RedisConnectionError(detail="Redis client not initialized")
        return self._client

    def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if self._client:
                self._client.ping()
                return True
            return False
        except redis.ConnectionError:
            return False


redis_client = RedisClient()


def get_redis() -> redis.Redis:
    """Dependency to get Redis client."""
    return redis_client.get_client()