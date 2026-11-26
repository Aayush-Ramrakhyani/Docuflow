"""
Document service: upload, retrieval, signed URLs, and deletion.

Authorization and quota enforcement live HERE, not in the endpoints — the service
is the trust boundary. Uploads are validated by magic bytes, stored under UUID
keys, and handed off to a Celery worker for async AI processing.
"""

import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.audit_repository import AuditRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.document import DocumentListResponse, DocumentResponse, SignedUrlResponse
from app.services.storage_service import StorageService
from app.utils.file_validation import safe_filename_extension, validate_upload

settings = get_settings()


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.docs = DocumentRepository(db)
        self.orgs = OrganizationRepository(db)
        self.audit = AuditRepository(db)
        self.storage = StorageService()

    async def upload(
        self,
        file: UploadFile,
        organization_id: uuid.UUID,
        uploader_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> tuple[DocumentResponse, uuid.UUID]:
        """
        Validate, store, and register a document upload.
        Returns (document, job_id) — job_id tracks the async processing task.
        """
        org = await self.orgs.get_by_id(organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Enforce the plan's document quota before accepting the file
        if org.documents_used >= org.documents_limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Document limit reached for your plan",
            )

        # Validate by magic bytes + size; detected_mime is trusted, client's is not
        content, detected_mime = await validate_upload(file)
        ext = safe_filename_extension(file.filename or "upload")

        # UUID-based storage key — the original filename never touches the path
        storage_key = self.storage.generate_storage_key(organization_id, ext)
        self.storage.upload_file(
            BytesIO(content),
            settings.S3_BUCKET_DOCUMENTS,
            storage_key,
            detected_mime,
        )

        # Keep the original name only as display metadata, capped in length
        safe_display_name = (file.filename or "upload")[:512]

        doc = await self.docs.create(
            organization_id=organization_id,
            uploaded_by_id=uploader_id,
            original_filename=safe_display_name,
            file_size_bytes=len(content),
            mime_type=detected_mime,
            storage_key=storage_key,
            storage_bucket=settings.S3_BUCKET_DOCUMENTS,
        )

        # Hand off to the Celery worker — the HTTP request returns without waiting
        from app.workers.document_processor import process_document_task

        job_result = process_document_task.delay(str(doc.id), str(organization_id))

        # Persist a job row so the UI can poll processing status
        from app.models.job import ProcessingJob

        job = ProcessingJob(
            document_id=doc.id,
            organization_id=organization_id,
            celery_task_id=job_result.id,
            task_name="process_document",
        )
        self.db.add(job)
        await self.db.flush()

        await self.docs.update_status(doc.id, "queued")

        await self.audit.log(
            action="document.upload",
            actor_id=uploader_id,
            organization_id=organization_id,
            resource_type="document",
            resource_id=str(doc.id),
            metadata={"filename": safe_display_name, "size_bytes": len(content), "mime": detected_mime},
            ip_address=ip_address,
        )

        return DocumentResponse.model_validate(doc), job.id

    async def get_signed_url(
        self,
        document_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> SignedUrlResponse:
        """Generate a short-lived signed URL AFTER verifying tenant ownership."""
        # Org-scoped lookup is the authorization check — no doc, no URL
        doc = await self.docs.get_by_id(document_id, organization_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        url = self.storage.generate_signed_download_url(
            doc.storage_bucket,
            doc.storage_key,
        )
        return SignedUrlResponse(
            url=url,
            expires_in=settings.SIGNED_URL_EXPIRATION_SECONDS,
        )

    async def list(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        document_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentListResponse:
        offset = (page - 1) * page_size  # Translate page number to row offset
        docs, total = await self.docs.list(
            organization_id=organization_id,
            status=status,
            document_type=document_type,
            search=search,
            offset=offset,
            limit=page_size,
        )
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(d) for d in docs],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,  # True when more rows remain
        )

    async def delete(
        self,
        document_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        # Verify ownership first
        doc = await self.docs.get_by_id(document_id, organization_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Remove the blob first; best-effort, so a missing object doesn't block DB cleanup
        self.storage.delete_file(doc.storage_bucket, doc.storage_key)

        await self.docs.delete(document_id, organization_id)

        await self.audit.log(
            action="document.delete",
            actor_id=actor_id,
            organization_id=organization_id,
            resource_type="document",
            resource_id=str(document_id),
            metadata={"filename": doc.original_filename},
        )
