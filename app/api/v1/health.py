from fastapi import APIRouter, Depends, status
from typing import Dict, Any
import redis

from app.config import settings
from app.core.redis_client import get_redis
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Check the health status of the application and it dependencies"
)
async def health_check(redis_client: redis.Redis = Depends(get_redis)) -> Dict[str, Any]:
    """Health check with dependency status"""
    health_status = {
        "status": "healthy",
        "service": "camb-kvstore-service",
        "version": settings.APP_VERSION,
        "dependencies": {}
    }

    try:
        redis_client.ping()
        health_status["dependencies"]["redis"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except redis.ConnectionError as e:
        health_status["status"] = "unhealthy"
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(f"Redis health check failed: {str(e)}")

    return health_status


@router.get(
    "/ready",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Readiness check endpoint",
    description="Check if the application is ready to accept traffic"
)
async def readiness_check(redis_client: redis.Redis = Depends(get_redis)) -> Dict[str, str]:
    """K8s readiness probe"""
    try:
        redis_client.ping()
        return {"status": "ready"}
    except redis.ConnectionError as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {"status": "not ready", "reason": "Redis unavailable"}


@router.get(
    "/live",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Liveness check endpoint",
    description="Check if the application is alive"
)
async def liveness_check() -> Dict[str, str]:
    """K8s liveness probe"""
    return {"status": "alive"}