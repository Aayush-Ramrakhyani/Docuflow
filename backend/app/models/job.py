"""
ProcessingJob tracks background Celery tasks for document processing.
Used for status polling and retry management.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class ProcessingJob(TimestampedModel):
    __tablename__ = "processing_jobs"

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

    # Celery task reference
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Job lifecycle
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )  # pending, running, completed, failed, retrying
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Internal structured error for debugging (never sent to client)
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="processing_jobs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} doc={self.document_id} status={self.status}>"
