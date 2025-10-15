from typing import Optional


class TokenData:
    """Token data model for JWT payload."""

    def __init__(
            self,
            tenant_id: str,
            username: Optional[str] = None,
            token_type: str = "access"
    ):
        self.tenant_id = tenant_id
        self.username = username
        self.token_type = token_type

    def to_dict(self) -> dict:
        """Convert token data to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "username": self.username,
            "token_type": self.token_type
        }