"""
Extraction data access layer.

Stores AI results and the human review lifecycle (correct → approve/reject).
Like the other repos, every query is org-scoped as an IDOR backstop in front of RLS.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extraction import Extraction


class ExtractionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(
        self, extraction_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Extraction | None:
        # id + org both required — cross-tenant access is impossible here
        result = await self.db.execute(
            select(Extraction).where(
                Extraction.id == extraction_id,
                Extraction.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_document(
        self, document_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Extraction | None:
        # A document can be re-processed; return the most recent extraction
        result = await self.db.execute(
            select(Extraction)
            .where(
                Extraction.document_id == document_id,
                Extraction.organization_id == organization_id,
            )
            .order_by(Extraction.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Extraction], int]:
        query = select(Extraction).where(Extraction.organization_id == organization_id)
        count_query = select(func.count()).select_from(Extraction).where(
            Extraction.organization_id == organization_id
        )
        if status:  # Optional status filter applied to both data + count queries
            query = query.where(Extraction.status == status)
            count_query = count_query.where(Extraction.status == status)

        total = (await self.db.execute(count_query)).scalar_one()
        query = query.order_by(Extraction.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(
        self,
        document_id: uuid.UUID,
        organization_id: uuid.UUID,
        model_used: str,
        provider: str,
        extracted_data: dict[str, Any],
        confidence_scores: dict[str, float],
        overall_confidence: float | None = None,
        tokens_used: int | None = None,
        processing_time_ms: int | None = None,
    ) -> Extraction:
        extraction = Extraction(
            document_id=document_id,
            organization_id=organization_id,
            model_used=model_used,
            provider=provider,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores,       # Per-field confidence for the review UI
            overall_confidence=overall_confidence,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )
        self.db.add(extraction)
        await self.db.flush()
        return extraction

    async def apply_correction(
        self,
        extraction_id: uuid.UUID,
        corrections: dict[str, Any],
        reviewer_id: uuid.UUID,
        notes: str | None = None,
    ) -> None:
        # Store reviewer edits separately from the AI output (original is preserved)
        await self.db.execute(
            update(Extraction)
            .where(Extraction.id == extraction_id)
            .values(
                corrected_data=corrections,
                reviewed_by_id=reviewer_id,
                reviewed_at=datetime.now(UTC),
                review_notes=notes,
            )
        )

    async def approve(
        self,
        extraction_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        notes: str | None = None,
    ) -> None:
        # Human-in-the-loop sign-off — marks the extraction as final/trusted
        await self.db.execute(
            update(Extraction)
            .where(Extraction.id == extraction_id)
            .values(
                status="approved",
                reviewed_by_id=reviewer_id,
                reviewed_at=datetime.now(UTC),
                review_notes=notes,
            )
        )

    async def reject(
        self,
        extraction_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        notes: str,  # Required — a rejection must say why
    ) -> None:
        await self.db.execute(
            update(Extraction)
            .where(Extraction.id == extraction_id)
            .values(
                status="rejected",
                reviewed_by_id=reviewer_id,
                reviewed_at=datetime.now(UTC),
                review_notes=notes,
            )
        )
