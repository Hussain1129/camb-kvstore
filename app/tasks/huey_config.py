from app.utils.logger import get_logger
from huey import RedisHuey, MemoryHuey
from app.config import settings
import os

logger = get_logger(__name__)

if settings.HUEY_IMMEDIATE or os.getenv('PYTEST_CURRENT_TEST'):
    huey = MemoryHuey(
        name='camb-kvstore-tasks',
        immediate=True
    )
    logger.info("Huey configured with MemoryHuey (immediate mode for tests)")

else:
    huey = RedisHuey(
        name='camb-kvstore-tasks',
        host=settings.HUEY_REDIS_HOST,
        port=settings.HUEY_REDIS_PORT,
        db=settings.HUEY_REDIS_DB,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        immediate=settings.HUEY_IMMEDIATE
    )
    logger.info(f"Huey configured with Redis at {settings.HUEY_REDIS_HOST}:{settings.HUEY_REDIS_PORT}")