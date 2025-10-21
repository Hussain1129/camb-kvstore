from fastapi import APIRouter, Depends, status, HTTPException, Query
from typing import Annotated, Optional, Dict
from app.schemas.kvstore import (
    KeyValueCreate,
    KeyValueUpdate,
    KeyValueResponse,
    KeyValueListResponse,
    KeyValueBatchCreate
)
from app.services.kvstore_service import KVStoreService
from app.api.deps import get_kvstore_service, get_tenant_id
from app.core.custom_exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
    KeyValueStoreError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _build_kv_response(kv_pair) -> KeyValueResponse:
    """Helper to convert KV model to response schema"""
    return KeyValueResponse(
        key=kv_pair.key,
        value=kv_pair.value,
        tenant_id=kv_pair.tenant_id,
        ttl=kv_pair.ttl,
        version=kv_pair.version,
        tags=kv_pair.tags,
        created_at=kv_pair.created_at,
        updated_at=kv_pair.updated_at,
        expires_at=kv_pair.expires_at
    )


@router.post(
    "",
    response_model=KeyValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create key-value pair",
    description="Create a new key-value pair for the current authenticated tenant"
)
async def create_key_value(
        kv_data: KeyValueCreate,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    try:
        kv_pair = kvstore_service.create(tenant_id, kv_data)
        return _build_kv_response(kv_pair)
    except ResourceAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyValueStoreError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{key}",
    response_model=KeyValueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get key-value pair",
    description="Retrieve a key-value pair by key"
)
async def get_key_value(
        key: str,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    try:
        kv_pair = kvstore_service.get(tenant_id, key)
        return _build_kv_response(kv_pair)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except KeyValueStoreError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/{key}",
    response_model=KeyValueResponse,
    status_code=status.HTTP_200_OK,
    summary="Update key-value pair",
    description="Update an existing key-value pair"
)
async def update_key_value(
        key: str,
        kv_update: KeyValueUpdate,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    try:
        kv_pair = kvstore_service.update(tenant_id, key, kv_update)
        return _build_kv_response(kv_pair)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyValueStoreError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete key-value pair",
    description="Delete a key-value pair by key from redis db"
)
async def delete_key_value(
        key: str,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    try:
        kvstore_service.delete(tenant_id, key)
        logger.info(f"Deleted {key} (tenant: {tenant_id})")
        return None
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except KeyValueStoreError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "",
    response_model=KeyValueListResponse,
    status_code=status.HTTP_200_OK,
    summary="List key-value pairs",
    description="List all key-value pairs for the authenticated tenant with pagination"
)
async def list_key_values(
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)],
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        tag_key: Optional[str] = Query(None, description="Filter by tag key"),
        tag_value: Optional[str] = Query(None, description="Filter by tag value")
):
    # TODO: optimize this for large tenant keysets - maybe use SCAN instead of SMEMBERS
    tag_filter = None
    if tag_key and tag_value:
        tag_filter = {tag_key: tag_value}

    kv_pairs, total = kvstore_service.list_keys(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        tag_filter=tag_filter
    )

    items = [_build_kv_response(kv) for kv in kv_pairs]

    return KeyValueListResponse(
        items=items,
        active=len(items),
        expired=total - len(items),
        page=page,
        page_size=page_size
    )


@router.post(
    "/batch",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Batch create key-value pairs",
    description="Create multiple key-value pairs in a single request"
)
async def batch_create_key_values(
        batch_data: KeyValueBatchCreate,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    created_pairs = kvstore_service.batch_create(tenant_id, batch_data.items)
    items = [_build_kv_response(kv) for kv in created_pairs]

    return {
        "created": len(created_pairs),
        "total": len(batch_data.items),
        "items": items
    }


@router.get(
    "/{key}/ttl",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get key TTL",
    description="Get remaining time-to-live for a key in seconds"
)
async def get_key_ttl(
        key: str,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    try:
        ttl = kvstore_service.get_ttl(tenant_id, key)
        return {"key": key, "ttl": ttl}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{key}/exists",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Check key existence",
    description="Check if a key exists in redis db"
)
async def check_key_exists(
        key: str,
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    exists = kvstore_service.exists(tenant_id, key)
    return {"key": key, "exists": exists}


@router.get(
    "/stats/count",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get key count",
    description="Get the total number of keys for the authenticated tenant"
)
async def get_key_count(
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        kvstore_service: Annotated[KVStoreService, Depends(get_kvstore_service)]
):
    count = kvstore_service.count_keys(tenant_id)
    return {"tenant_id": tenant_id, "count": count}