"""
Immutable audit log. Rows are INSERT-only — never update or delete.
RLS: members can read their org's log; superadmins read all.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. user.login, document.upload, extraction.approve, api_key.create

    # Affected resource
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Additional context (IP, user agent, changed fields, etc.)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Outcome
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Network context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} actor={self.actor_id}>"
