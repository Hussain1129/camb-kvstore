from datetime import datetime
from typing import Optional
from pydantic import EmailStr

class User:
    """User/Tenant model for authentication and data isolation."""

    def __init__(
            self,
            tenant_id: str,
            username: str,
            email: EmailStr,
            hashed_password: str,
            is_active: bool = True,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None
    ):
        self.tenant_id = tenant_id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def __str__(self):
        return f"User: {self.username}"

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create user from dictionary."""
        return cls(
            tenant_id=data["tenant_id"],
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None
        )