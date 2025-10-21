import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import redis
from app.models.kvstore import KeyValuePair
from app.schemas.kvstore import KeyValueCreate, KeyValueUpdate
from app.core.custom_exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
    KeyValueStoreError
)
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KVStoreService:
    """Service for key-value store operations with multi-tenancy support."""

    KV_PREFIX = "kv"
    METADATA_SUFFIX = "metadata"
    TENANT_KEYS_SET = "tenant_keys"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _get_kv_key(self, tenant_id: str, key: str) -> str:
        return f"{self.KV_PREFIX}:{tenant_id}:{key}"

    def _get_metadata_key(self, tenant_id: str, key: str) -> str:
        return f"{self.KV_PREFIX}:{tenant_id}:{key}:{self.METADATA_SUFFIX}"

    def _get_tenant_keys_set(self, tenant_id: str) -> str:
        return f"{self.TENANT_KEYS_SET}:{tenant_id}"

    def create(self, tenant_id: str, kv_data: KeyValueCreate) -> KeyValuePair:
        """Create a new key-value pair for a tenant."""
        kv_key = self._get_kv_key(tenant_id, kv_data.key)
        metadata_key = self._get_metadata_key(tenant_id, kv_data.key)

        if self.redis.exists(kv_key):
            raise ResourceAlreadyExistsError(detail=f"Key '{kv_data.key}' already exists")

        now = datetime.utcnow()
        expires_at = None

        if kv_data.ttl:
            expires_at = now + timedelta(seconds=kv_data.ttl)

        try:
            kv_pair = KeyValuePair(
                key=kv_data.key,
                value=kv_data.value,
                tenant_id=tenant_id,
                ttl=kv_data.ttl,
                version=1,
                tags=kv_data.tags or {},
                created_at=now,
                updated_at=now,
                expires_at=expires_at
            )

            metadata = {
                "tenant_id": tenant_id,
                "ttl": kv_data.ttl,
                "version": 1,
                "tags": json.dumps(kv_data.tags or {}),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None
            }

            # use pipeline to make these atomic
            pipeline = self.redis.pipeline()

            if kv_data.ttl:
                pipeline.setex(kv_key, kv_data.ttl, kv_data.value)
                pipeline.setex(metadata_key, kv_data.ttl, json.dumps(metadata))
            else:
                pipeline.set(kv_key, kv_data.value)
                pipeline.set(metadata_key, json.dumps(metadata))

            pipeline.sadd(self._get_tenant_keys_set(tenant_id), kv_data.key)
            pipeline.execute()

            logger.info(f"Created '{kv_data.key}' (tenant={tenant_id})")

            return kv_pair

        except redis.RedisError as e:
            logger.error(f"create failed for {kv_data.key}: {str(e)}")
            raise KeyValueStoreError(detail=f"Failed to create key: {str(e)}")

    def get(self, tenant_id: str, key: str) -> KeyValuePair:
        """Retrieve a key-value pair by key."""
        kv_key = self._get_kv_key(tenant_id, key)
        metadata_key = self._get_metadata_key(tenant_id, key)

        try:
            pipeline = self.redis.pipeline()
            pipeline.get(kv_key)
            pipeline.get(metadata_key)
            results = pipeline.execute()

            value, metadata_json = results

            if value is None:
                raise ResourceNotFoundError(detail=f"Key '{key}' not found")

            metadata = json.loads(metadata_json) if metadata_json else {}

            kv_pair = KeyValuePair(
                key=key,
                value=value,
                tenant_id=tenant_id,
                ttl=metadata.get("ttl"),
                version=metadata.get("version", 1),
                tags=json.loads(metadata.get("tags", "{}")),
                created_at=datetime.fromisoformat(
                    metadata["created_at"]) if "created_at" in metadata else datetime.utcnow(),
                updated_at=datetime.fromisoformat(
                    metadata["updated_at"]) if "updated_at" in metadata else datetime.utcnow(),
                expires_at=datetime.fromisoformat(metadata["expires_at"]) if metadata.get("expires_at") else None
            )

            logger.debug(f"Key retrieved: {key} for tenant: {tenant_id}")

            return kv_pair

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode metadata for key {key}: {str(e)}")
            raise KeyValueStoreError(detail="Failed to decode key metadata")
        except redis.RedisError as e:
            logger.error(f"Failed to retrieve key {key}: {str(e)}")
            raise KeyValueStoreError(detail=f"Failed to retrieve key: {str(e)}")

    def update(self, tenant_id: str, key: str, kv_update: KeyValueUpdate) -> KeyValuePair:
        """Update an existing key-value pair."""
        kv_key = self._get_kv_key(tenant_id, key)
        metadata_key = self._get_metadata_key(tenant_id, key)

        if not self.redis.exists(kv_key):
            raise ResourceNotFoundError(detail=f"Key '{key}' not found")

        try:
            metadata_json = self.redis.get(metadata_key)
            metadata = json.loads(metadata_json) if metadata_json else {}

            now = datetime.utcnow()
            version = metadata.get("version", 1) + 1

            if kv_update.value is not None:
                new_value = kv_update.value
            else:
                new_value = self.redis.get(kv_key)

            if kv_update.ttl is not None:
                new_ttl = kv_update.ttl
                expires_at = now + timedelta(seconds=new_ttl)
            else:
                new_ttl = metadata.get("ttl")
                expires_at = datetime.fromisoformat(metadata["expires_at"]) if metadata.get("expires_at") else None

            if kv_update.tags is not None:
                new_tags = kv_update.tags
            else:
                new_tags = json.loads(metadata.get("tags", "{}"))

            updated_metadata = {
                "tenant_id": tenant_id,
                "ttl": new_ttl,
                "version": version,
                "tags": json.dumps(new_tags),
                "created_at": metadata.get("created_at", now.isoformat()),
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None
            }

            pipeline = self.redis.pipeline()

            if new_ttl:
                pipeline.setex(kv_key, new_ttl, new_value)
                pipeline.setex(metadata_key, new_ttl, json.dumps(updated_metadata))
            else:
                pipeline.set(kv_key, new_value)
                pipeline.set(metadata_key, json.dumps(updated_metadata))

            pipeline.execute()

            kv_pair = KeyValuePair(
                key=key,
                value=new_value,
                tenant_id=tenant_id,
                ttl=new_ttl,
                version=version,
                tags=new_tags,
                created_at=datetime.fromisoformat(updated_metadata["created_at"]),
                updated_at=now,
                expires_at=expires_at
            )

            logger.info(f"Key updated: {key} for tenant: {tenant_id}, version: {version}")

            return kv_pair

        except redis.RedisError as e:
            logger.error(f"Failed to update key {key}: {str(e)}")
            raise KeyValueStoreError(detail=f"Failed to update key: {str(e)}")

    def delete(self, tenant_id: str, key: str) -> bool:
        """Delete a key-value pair."""
        kv_key = self._get_kv_key(tenant_id, key)
        metadata_key = self._get_metadata_key(tenant_id, key)

        if not self.redis.exists(kv_key):
            raise ResourceNotFoundError(detail=f"Key '{key}' not found")

        try:
            pipeline = self.redis.pipeline()
            pipeline.delete(kv_key)
            pipeline.delete(metadata_key)
            pipeline.srem(self._get_tenant_keys_set(tenant_id), key)
            pipeline.execute()

            logger.info(f"Key deleted: {key} for tenant: {tenant_id}")

            return True

        except redis.RedisError as e:
            logger.error(f"Failed to delete key {key}: {str(e)}")
            raise KeyValueStoreError(detail=f"Failed to delete key: {str(e)}")

    def list_keys(
            self,
            tenant_id: str,
            page: int = 1,
            page_size: int = 20,
            tag_filter: Optional[Dict[str, str]] = None
    ) -> tuple[List[KeyValuePair], int]:
        """List all keys for a tenant with pagination and optional tag filtering."""
        try:
            # FIXME: this will be slow for tenants with huge keysets
            # should probably use SCAN instead of SMEMBERS
            all_keys = list(self.redis.smembers(self._get_tenant_keys_set(tenant_id)))

            if tag_filter:
                # filter by tags - this is inefficient but works for now
                filtered_keys = []
                for key in all_keys:
                    try:
                        kv_pair = self.get(tenant_id, key)
                        if all(kv_pair.tags.get(k) == v for k, v in tag_filter.items()):
                            filtered_keys.append(key)
                    except ResourceNotFoundError:
                        continue
                all_keys = filtered_keys

            total = len(all_keys)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_keys = all_keys[start_idx:end_idx]

            kv_pairs = []
            for key in paginated_keys:
                try:
                    kv_pair = self.get(tenant_id, key)
                    kv_pairs.append(kv_pair)
                except ResourceNotFoundError:
                    continue

            logger.debug(f"Listed {len(kv_pairs)} keys for tenant: {tenant_id}")

            return kv_pairs, total

        except redis.RedisError as e:
            logger.error(f"Failed to list keys for tenant {tenant_id}: {str(e)}")
            raise KeyValueStoreError(detail=f"Failed to list keys: {str(e)}")

    def batch_create(self, tenant_id: str, items: List[KeyValueCreate]) -> List[KeyValuePair]:
        """Batch create multiple key-value pairs."""
        created_pairs = []
        errors = []

        for item in items:
            try:
                kv_pair = self.create(tenant_id, item)
                created_pairs.append(kv_pair)
            except (ResourceAlreadyExistsError, ValidationError) as e:
                errors.append({"key": item.key, "error": str(e)})
                logger.warning(f"Failed to create key {item.key} in batch: {str(e)}")

        if errors and not created_pairs:
            raise KeyValueStoreError(detail=f"Batch create failed: {errors}")

        logger.info(f"Batch created {len(created_pairs)} keys for tenant: {tenant_id}")

        return created_pairs

    def exists(self, tenant_id: str, key: str) -> bool:
        """Check if a key exists for a tenant."""
        kv_key = self._get_kv_key(tenant_id, key)
        return self.redis.exists(kv_key) > 0

    def get_ttl(self, tenant_id: str, key: str) -> Optional[int]:
        """Get remaining TTL for a key in seconds."""
        kv_key = self._get_kv_key(tenant_id, key)
        ttl = self.redis.ttl(kv_key)

        if ttl == -2:
            raise ResourceNotFoundError(detail=f"Key '{key}' not found")

        if ttl == -1:
            return None

        return ttl

    def count_keys(self, tenant_id: str) -> int:
        """Count total keys for a tenant."""
        return self.redis.scard(self._get_tenant_keys_set(tenant_id))