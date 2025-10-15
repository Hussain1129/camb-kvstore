from app.core.custom_exceptions import RedisConnectionError
from app.core.redis_client import redis_client
import redis
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_redis_connection():
    try:
        client = redis_client.get_client()
        return client

    except redis.exceptions.ConnectionError as err:
        logger.error(f"Redis connection error in TTL cleanup: {str(err)}")
        raise RedisConnectionError("Redis connection error in TTL cleanup")