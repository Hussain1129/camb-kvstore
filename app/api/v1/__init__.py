from fastapi import APIRouter
from app.api.v1 import auth, kvstore, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(kvstore.router, prefix="/kv", tags=["Key-Value Store"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])