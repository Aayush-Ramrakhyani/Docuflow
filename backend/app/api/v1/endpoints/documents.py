"""Document upload, listing, detail, download, and deletion endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_member
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    SignedUrlResponse,
)
from app.services.document_service import DocumentService

settings = get_settings()
router = APIRouter(prefix="/organizations/{organization_id}/documents", tags=["Documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    organization_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File(description="PDF, JPEG, PNG, TIFF, or WebP")],
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    svc = DocumentService(db)
    doc, job_id = await svc.upload(
        file=file,
        organization_id=organization_id,
        uploader_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return DocumentUploadResponse(document=doc, job_id=job_id)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    organization_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    svc = DocumentService(db)
    return await svc.list(
        organization_id=organization_id,
        status=status,
        document_type=document_type,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    organization_id: UUID,
    document_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.repositories.document_repository import DocumentRepository

    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id, organization_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/download", response_model=SignedUrlResponse)
async def get_document_download_url(
    organization_id: UUID,
    document_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Returns a short-lived signed URL for direct document download.
    Authorization is verified before generating the URL.
    """
    svc = DocumentService(db)
    return await svc.get_signed_url(document_id, organization_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    organization_id: UUID,
    document_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, membership = auth
    # Only admins/owners can delete documents
    if membership.role not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to delete documents",
        )
    svc = DocumentService(db)
    await svc.delete(document_id, organization_id, current_user.id)
