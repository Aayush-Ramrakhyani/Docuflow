"""
API key model for programmatic access.
Only the hash of the key is stored; the raw key is shown to the user once.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class APIKey(TimestampedModel):
    __tablename__ = "api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Prefix shown in the UI (first 8 chars of raw key) for identification
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # Argon2id hash of the full key — never the raw key
    hashed_key: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scopes: comma-separated e.g. "documents:read,documents:write,extractions:read"
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="documents:read")

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} prefix={self.key_prefix} org={self.organization_id}>"
