"""
Document model: represents an uploaded file tied to an organization.
Original filename stored as metadata only; storage uses UUID-based keys.
"""

import uuid
from typing import Literal

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

DocumentStatus = Literal[
    "uploaded",       # File received, not yet processed
    "queued",         # Sent to processing queue
    "processing",     # Worker is actively processing
    "processed",      # Processing complete, extraction available
    "review_pending", # Awaiting human review/approval
    "approved",       # Extraction approved
    "rejected",       # Extraction rejected; needs re-upload or manual entry
    "failed",         # Processing failed permanently
]


class Document(TimestampedModel):
    __tablename__ = "documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # File metadata (untrusted values from client stored as-is for display only)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Storage key — UUID-based, never the original filename
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)

    # Document classification
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # invoice, contract, etc.

    # Processing status
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded", index=True)
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", back_populates="documents"
    )
    extractions: Mapped[list["Extraction"]] = relationship(  # noqa: F821
        "Extraction", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(  # noqa: F821
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.original_filename} status={self.status}>"
