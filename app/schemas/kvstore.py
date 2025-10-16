from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime
from app.config import settings


class KeyValueBase(BaseModel):
    """Base key-value schema."""
    key: str = Field(..., min_length=1, max_length=256, description="Unique key identifier")
    value: str = Field(..., description="Value to store")


class KeyValueCreate(KeyValueBase):
    """Schema for creating a new key-value pair."""
    ttl: Optional[int] = Field(
        None,
        gt=0,
        description="Time to live in seconds"
    )
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Optional metadata tags"
    )

    @validator("key")
    def validate_key(cls, v):
        if len(v.encode('utf-8')) > settings.MAX_KEY_SIZE:
            raise ValueError(f"Key size exceeds maximum of {settings.MAX_KEY_SIZE} bytes")
        if not v.strip():
            raise ValueError("Key cannot be empty or whitespace only")
        return v.strip()

    @validator("value")
    def validate_value(cls, v):
        if len(v.encode('utf-8')) > settings.MAX_VALUE_SIZE:
            raise ValueError(f"Value size exceeds maximum of {settings.MAX_VALUE_SIZE} bytes")
        return v

    @validator("tags")
    def validate_tags(cls, v):
        if v and len(v) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for key, value in (v or {}).items():
            if len(key) > 100 or len(value) > 100:
                raise ValueError("Tag key and value must be less than 100 characters")
        return v


class KeyValueUpdate(BaseModel):
    """Schema for updating a key-value pair."""
    value: Optional[str] = Field(None, description="Updated value")
    ttl: Optional[int] = Field(None, gt=0, description="Updated TTL in seconds")
    tags: Optional[Dict[str, str]] = Field(None, description="Updated metadata tags")

    @validator("value")
    def validate_value(cls, v):
        if v is not None and len(v.encode('utf-8')) > settings.MAX_VALUE_SIZE:
            raise ValueError(f"Value size exceeds maximum of {settings.MAX_VALUE_SIZE} bytes")
        return v

    @validator("tags")
    def validate_tags(cls, v):
        if v and len(v) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for key, value in (v or {}).items():
            if len(key) > 100 or len(value) > 100:
                raise ValueError("Tag key and value must be less than 100 characters")
        return v


class KeyValueResponse(KeyValueBase):
    """Schema for key-value response."""
    tenant_id: str = Field(..., description="Tenant identifier")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    version: int = Field(..., description="Version number")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metadata tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "key": "user:123:profile",
                "value": "John Doe",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "ttl": 3600,
                "version": 1,
                "tags": {"category": "user", "environment": "development"},
                "created_at": "2025-01-01T12:00:00",
                "updated_at": "2025-01-01T12:00:00",
                "expires_at": "2025-01-01T13:00:00"
            }
        }


class KeyValueListResponse(BaseModel):
    """Schema for listing key-value pairs."""
    items: List[KeyValueResponse] = Field(..., description="List of key-value pairs")
    active: int = Field(..., description="Total number of active items")
    expired: int = Field(..., description="Total number of expired items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "active": 100,
                "expired": 5,
                "page": 1,
                "page_size": 20
            }
        }


class KeyValueBatchCreate(BaseModel):
    """Schema for batch creating key-value pairs."""
    items: List[KeyValueCreate] = Field(..., min_length=1, max_length=100,
                                        description="List of key-value pairs to create")

    @validator("items")
    def validate_items(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 items allowed per batch operation")

        keys = [item.key for item in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys found in batch")

        return v