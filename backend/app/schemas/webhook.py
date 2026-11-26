"""
Webhook configuration & delivery schemas.

Subscribed event names are validated against a fixed allowlist (VALID_EVENTS) so
a client can't register for an event the system will never emit. The signing
secret is returned exactly once, at creation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

# The complete set of events a webhook may subscribe to.
VALID_EVENTS = {
    "document.uploaded",
    "document.processing_started",
    "document.processed",
    "document.failed",
    "extraction.completed",
    "extraction.approved",
    "extraction.rejected",
    "member.invited",
    "member.removed",
}


class CreateWebhookRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, strip_whitespace=True)
    url: str = Field(min_length=10, max_length=2048)       # Destination endpoint
    events: list[str] = Field(min_length=1)                # Must subscribe to ≥1 event
    timeout_seconds: int = Field(default=30, ge=5, le=120)  # Bounded delivery timeout

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        # Reject any event name not in the allowlist
        for event in v:
            if event not in VALID_EVENTS:
                raise ValueError(f"Unknown event type: {event}. Valid events: {sorted(VALID_EVENTS)}")
        return list(set(v))  # Deduplicate


class UpdateWebhookRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=10, max_length=2048)
    events: list[str] | None = None
    is_active: bool | None = None

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        if v is None:  # Field omitted on update → leave unchanged
            return v
        for event in v:
            if event not in VALID_EVENTS:
                raise ValueError(f"Unknown event type: {event}")
        return list(set(v))


class WebhookCreatedResponse(BaseModel):
    """Returned once at creation — raw_secret is never retrievable again."""
    id: UUID
    name: str
    url: str
    events: list[str]
    raw_secret: str  # Shown only here; used by the receiver to verify HMAC signatures
    created_at: str


class WebhookResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    timeout_seconds: int
    successful_deliveries: int   # Delivery stats for the settings UI
    failed_deliveries: int
    last_triggered_at: datetime | None
    created_at: str


class WebhookDeliveryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    webhook_id: UUID
    event_type: str
    event_id: str                      # Unique per event — enables receiver-side idempotency
    status: str
    attempt: int
    response_status_code: int | None
    error_message: str | None
    delivered_at: datetime | None
    created_at: str
