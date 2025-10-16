import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration."""

    APP_NAME: str = os.getenv("APP_NAME", "CAMB KVStore")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str =  os.getenv("ENVIRONMENT", "prod")
    DEBUG: bool = bool(os.getenv("DEBUG")) if os.getenv("DEBUG") is not None else False
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = os.getenv("PORT", "8080")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret123123")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 10)

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = os.getenv("REDIS_PORT", "6379")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_DB: int = os.getenv("REDIS_DB", 1)
    REDIS_MAX_CONNECTIONS: int = os.getenv("REDIS_MAX_CONNECTIONS", 100)
    REDIS_SOCKET_TIMEOUT: int = os.getenv("REDIS_SOCKET_TIMEOUT", 10)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 10)

    HUEY_REDIS_HOST: str = os.getenv("HUEY_REDIS_HOST", "localhost")
    HUEY_REDIS_PORT: int = os.getenv("HUEY_REDIS_PORT", "6379")
    HUEY_REDIS_DB: int = os.getenv("HUEY_REDIS_DB", 1)
    HUEY_IMMEDIATE: bool = bool(os.getenv("HUEY_IMMEDIATE")) if os.getenv("HUEY_IMMEDIATE") is not None else True
    HUEY_WORKERS: int = os.getenv("HUEY_WORKERS", 1)

    DEFAULT_TTL_SECONDS: int = os.getenv("DEFAULT_TTL_SECONDS", 3600)
    MAX_KEY_SIZE: int = os.getenv("MAX_KEY_SIZE", 256)
    MAX_VALUE_SIZE: int = os.getenv("MAX_VALUE_SIZE", 2097152)
    CLEANUP_INTERVAL_SECONDS: int = os.getenv("CLEANUP_INTERVAL_SECONDS", 200)

    ENABLE_METRICS: bool = bool(os.getenv("ENABLE_METRICS")) if os.getenv("ENABLE_METRICS") is not None else False
    METRICS_PORT: int = os.getenv("METRICS_PORT", "9000")

    RATE_LIMIT_ENABLED: bool = bool(os.getenv("RATE_LIMIT_ENABLED")) if os.getenv("RATE_LIMIT_ENABLED") is not None else False
    RATE_LIMIT_REQUESTS: int = os.getenv("RATE_LIMIT_REQUESTS", "1000")
    RATE_LIMIT_PERIOD: int = os.getenv("RATE_LIMIT_PERIOD", "45")

    @property
    def redis_url(self) -> str:
        """Constructing the redis url."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def huey_redis_url(self) -> str:
        """Constructing the huey redis url."""
        return f"redis://{self.HUEY_REDIS_HOST}:{self.HUEY_REDIS_PORT}/{self.HUEY_REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get the cached settings instance."""
    return Settings()


settings = get_settings()