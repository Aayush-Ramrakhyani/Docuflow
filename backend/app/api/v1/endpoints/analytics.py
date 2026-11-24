"""Analytics and dashboard statistics endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_member
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.job import ProcessingJob

router = APIRouter(prefix="/organizations/{organization_id}/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview(
    organization_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Dashboard KPIs: total documents, processing status breakdown, extraction stats."""

    # Total documents
    total_docs = (
        await db.execute(
            select(func.count()).select_from(Document).where(
                Document.organization_id == organization_id
            )
        )
    ).scalar_one()

    # Documents by status
    status_rows = (
        await db.execute(
            select(Document.status, func.count().label("count"))
            .where(Document.organization_id == organization_id)
            .group_by(Document.status)
        )
    ).fetchall()
    status_breakdown = {row.status: row.count for row in status_rows}

    # Total extractions
    total_extractions = (
        await db.execute(
            select(func.count()).select_from(Extraction).where(
                Extraction.organization_id == organization_id
            )
        )
    ).scalar_one()

    # Avg confidence
    avg_confidence = (
        await db.execute(
            select(func.avg(Extraction.overall_confidence)).where(
                Extraction.organization_id == organization_id,
                Extraction.overall_confidence.is_not(None),
            )
        )
    ).scalar_one()

    # Pending review count
    pending_review = status_breakdown.get("review_pending", 0)

    # Processing jobs breakdown
    job_rows = (
        await db.execute(
            select(ProcessingJob.status, func.count().label("count"))
            .where(ProcessingJob.organization_id == organization_id)
            .group_by(ProcessingJob.status)
        )
    ).fetchall()
    job_breakdown = {row.status: row.count for row in job_rows}

    # Document type breakdown
    type_rows = (
        await db.execute(
            select(Document.document_type, func.count().label("count"))
            .where(
                Document.organization_id == organization_id,
                Document.document_type.is_not(None),
            )
            .group_by(Document.document_type)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).fetchall()
    type_breakdown = {row.document_type: row.count for row in type_rows}

    return {
        "total_documents": total_docs,
        "pending_review": pending_review,
        "total_extractions": total_extractions,
        "average_confidence": round(float(avg_confidence or 0), 3),
        "status_breakdown": status_breakdown,
        "job_breakdown": job_breakdown,
        "document_type_breakdown": type_breakdown,
    }
