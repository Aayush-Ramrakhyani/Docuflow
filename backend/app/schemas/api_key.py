"""API key creation and listing schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, strip_whitespace=True)
    scopes: list[str] = Field(
        default=["documents:read"],
        min_length=1,
    )
    expires_at: datetime | None = None

    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        allowed = {
            "documents:read", "documents:write",
            "extractions:read", "extractions:write",
            "webhooks:read", "webhooks:write",
            "analytics:read",
        }
        for scope in v:
            if scope not in allowed:
                raise ValueError(f"Unknown scope: {scope}")
        return v


class APIKeyCreatedResponse(BaseModel):
    """Returned once at creation. raw_key is never stored and cannot be retrieved again."""
    id: UUID
    name: str
    key_prefix: str
    raw_key: str  # shown only on creation
    scopes: list[str]
    expires_at: datetime | None
    created_at: str


class APIKeyResponse(BaseModel):
    """Safe response — no raw key."""
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    key_prefix: str
    scopes: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: str
