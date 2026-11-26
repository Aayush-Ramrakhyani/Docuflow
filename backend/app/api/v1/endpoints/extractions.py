"""
Extraction endpoints: list, fetch, correct, approve, reject.

This is the human-in-the-loop review surface. Every route is org-scoped via
require_member, and every mutating action is written to the audit log. Approve/
reject also drive the parent document's status.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_member
from app.repositories.extraction_repository import ExtractionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.extraction import (
    ApproveExtractionRequest,
    CorrectExtractionRequest,
    ExtractionListResponse,
    ExtractionResponse,
    RejectExtractionRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/extractions", tags=["Extractions"])


@router.get("", response_model=ExtractionListResponse)
async def list_extractions(
    organization_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),  # Capped so clients can't request huge pages
):
    repo = ExtractionRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.list(organization_id, status=status, offset=offset, limit=page_size)
    return ExtractionListResponse(
        items=[ExtractionResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


@router.get("/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction(
    organization_id: UUID,
    extraction_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ExtractionRepository(db)
    # Org-scoped fetch — returns None (→404) for another tenant's extraction
    extraction = await repo.get_by_id(extraction_id, organization_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return ExtractionResponse.model_validate(extraction)


@router.get("/by-document/{document_id}", response_model=ExtractionResponse)
async def get_extraction_for_document(
    organization_id: UUID,
    document_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Verify the document belongs to this org first (explicit IDOR check)
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id, organization_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    repo = ExtractionRepository(db)
    extraction = await repo.get_latest_for_document(document_id, organization_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="No extraction found for this document")
    return ExtractionResponse.model_validate(extraction)


@router.patch("/{extraction_id}/correct", response_model=ExtractionResponse)
async def correct_extraction(
    organization_id: UUID,
    extraction_id: UUID,
    body: CorrectExtractionRequest,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    repo = ExtractionRepository(db)
    extraction = await repo.get_by_id(extraction_id, organization_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    if extraction.status == "approved":  # Approved data is locked — can't be edited
        raise HTTPException(status_code=409, detail="Cannot correct an approved extraction")

    # Merge new corrections over any prior ones so partial edits accumulate
    existing_corrections = extraction.corrected_data or {}
    merged = {**existing_corrections, **body.corrections}

    await repo.apply_correction(extraction_id, merged, current_user.id, body.notes)

    audit = AuditRepository(db)
    await audit.log(
        action="extraction.correct",
        actor_id=current_user.id,
        organization_id=organization_id,
        resource_type="extraction",
        resource_id=str(extraction_id),
        metadata={"fields_corrected": list(body.corrections.keys())},  # Log which fields changed, not values
    )

    updated = await repo.get_by_id(extraction_id, organization_id)
    return ExtractionResponse.model_validate(updated)


@router.post("/{extraction_id}/approve", response_model=ExtractionResponse)
async def approve_extraction(
    organization_id: UUID,
    extraction_id: UUID,
    body: ApproveExtractionRequest,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    repo = ExtractionRepository(db)
    extraction = await repo.get_by_id(extraction_id, organization_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    if extraction.status == "approved":  # Idempotency guard against double-approve
        raise HTTPException(status_code=409, detail="Already approved")

    await repo.approve(extraction_id, current_user.id, body.notes)

    # Approving the extraction promotes the parent document to "approved" too
    doc_repo = DocumentRepository(db)
    await doc_repo.update_status(extraction.document_id, "approved")

    audit = AuditRepository(db)
    await audit.log(
        action="extraction.approve",
        actor_id=current_user.id,
        organization_id=organization_id,
        resource_type="extraction",
        resource_id=str(extraction_id),
    )

    updated = await repo.get_by_id(extraction_id, organization_id)
    return ExtractionResponse.model_validate(updated)


@router.post("/{extraction_id}/reject", response_model=ExtractionResponse)
async def reject_extraction(
    organization_id: UUID,
    extraction_id: UUID,
    body: RejectExtractionRequest,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    repo = ExtractionRepository(db)
    extraction = await repo.get_by_id(extraction_id, organization_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    await repo.reject(extraction_id, current_user.id, body.notes)

    # Rejection cascades to the document status as well
    doc_repo = DocumentRepository(db)
    await doc_repo.update_status(extraction.document_id, "rejected")

    audit = AuditRepository(db)
    await audit.log(
        action="extraction.reject",
        actor_id=current_user.id,
        organization_id=organization_id,
        resource_type="extraction",
        resource_id=str(extraction_id),
        metadata={"reason": body.notes},  # Capture why it was rejected
    )

    updated = await repo.get_by_id(extraction_id, organization_id)
    return ExtractionResponse.model_validate(updated)
