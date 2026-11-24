"""
Webhook models: configuration and delivery tracking.
Outgoing webhooks are signed with HMAC-SHA256.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class Webhook(TimestampedModel):
    __tablename__ = "webhooks"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Argon2id hash of the HMAC secret — raw secret shown once at creation
    hashed_secret: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSON array of event names this webhook subscribes to
    # e.g. ["document.uploaded", "extraction.completed", "extraction.approved"]
    events: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Delivery settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Stats
    successful_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Webhook id={self.id} url={self.url[:40]}>"


class WebhookDelivery(TimestampedModel):
    __tablename__ = "webhook_deliveries"

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # Payload sent (stored for debugging/replay)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Delivery outcome
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    # pending, delivered, failed, retrying
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery id={self.id} event={self.event_type} status={self.status}>"
