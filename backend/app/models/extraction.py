"""
Extraction model: stores AI-extracted fields for a document.
extracted_data is JSONB — flexible for different document schemas.
Field-level confidence is tracked separately for the review UI.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

ExtractionStatus = str  # "pending_review", "approved", "rejected", "needs_correction"


class Extraction(TimestampedModel):
    __tablename__ = "extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # AI model metadata
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="anthropic")

    # Extracted data as JSONB — varies by document type
    extracted_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Field-level confidence scores {field_name: confidence_0_to_1}
    confidence_scores: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Overall extraction confidence (0.0–1.0)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Processing metadata
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(nullable=True)

    # Review lifecycle
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review", index=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Human-corrected data (applied on top of extracted_data when corrections made)
    corrected_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="extractions")  # noqa: F821

    @property
    def final_data(self) -> dict[str, Any]:
        """Returns corrected data if available, otherwise extracted_data."""
        if self.corrected_data:
            return {**self.extracted_data, **self.corrected_data}
        return self.extracted_data

    def __repr__(self) -> str:
        return f"<Extraction id={self.id} doc={self.document_id} status={self.status}>"
