from datetime import datetime
from typing import Optional, Dict, Any


class KeyValuePair:
    """Key-Value pair model with metadata support."""

    def __init__(
            self,
            key: str,
            value: str,
            tenant_id: str,
            ttl: Optional[int] = None,
            version: int = 1,
            tags: Optional[Dict[str, str]] = None,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None,
            expires_at: Optional[datetime] = None
    ):
        self.key = key
        self.value = value
        self.tenant_id = tenant_id
        self.ttl = ttl
        self.version = version
        self.tags = tags or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.expires_at = expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert KV pair to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "tenant_id": self.tenant_id,
            "ttl": self.ttl,
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyValuePair":
        """Create KV pair from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            tenant_id=data["tenant_id"],
            ttl=data.get("ttl"),
            version=data.get("version", 1),
            tags=data.get("tags", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        )