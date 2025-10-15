from app.utils.logger import get_logger
from huey import RedisHuey
from app.config import settings

logger = get_logger(__name__)

huey = RedisHuey(
    name='camb-kvstore-tasks',
    host=settings.HUEY_REDIS_HOST,
    port=settings.HUEY_REDIS_PORT,
    db=settings.HUEY_REDIS_DB,
    immediate=settings.HUEY_IMMEDIATE
)

logger.info(f"Huey configured with Redis at {settings.HUEY_REDIS_HOST}:{settings.HUEY_REDIS_PORT}")