"""
API key creation & listing schemas.

Requested scopes are validated against a fixed allowlist. The raw key is returned
exactly once at creation and never again — only its prefix + hash are persisted.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Every permission an API key may be granted.
_ALLOWED_SCOPES = {
    "documents:read", "documents:write",
    "extractions:read", "extractions:write",
    "webhooks:read", "webhooks:write",
    "analytics:read",
}


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, strip_whitespace=True)
    scopes: list[str] = Field(
        default=["documents:read"],  # Least-privilege default
        min_length=1,
    )
    expires_at: datetime | None = None  # Optional expiry; None = never expires

    @field_validator("scopes")  # Decorator is required — without it the check never runs
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        # Reject any scope outside the allowlist
        for scope in v:
            if scope not in _ALLOWED_SCOPES:
                raise ValueError(f"Unknown scope: {scope}")
        return v


class APIKeyCreatedResponse(BaseModel):
    """Returned once at creation — raw_key is never stored and can't be retrieved again."""
    id: UUID
    name: str
    key_prefix: str      # First chars of the key, shown in the UI for identification
    raw_key: str         # Full key — displayed only here, immediately after creation
    scopes: list[str]
    expires_at: datetime | None
    created_at: str


class APIKeyResponse(BaseModel):
    """Safe listing response — never includes the raw key."""
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    key_prefix: str
    scopes: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: str
