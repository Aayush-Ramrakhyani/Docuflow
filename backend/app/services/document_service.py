"""
Document upload, retrieval, deletion, and signed URL generation.
Authorization is enforced here — never trust caller to pre-check.
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
        Returns (document, job_id) — the job_id is used to track async processing.
        """
        org = await self.orgs.get_by_id(organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        if org.documents_used >= org.documents_limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Document limit reached for your plan",
            )

        content, detected_mime = await validate_upload(file)
        ext = safe_filename_extension(file.filename or "upload")

        storage_key = self.storage.generate_storage_key(organization_id, ext)
        self.storage.upload_file(
            BytesIO(content),
            settings.S3_BUCKET_DOCUMENTS,
            storage_key,
            detected_mime,
        )

        # Safe: original_filename is stored only as display metadata, never used as a path
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

        # Dispatch async processing job
        from app.workers.document_processor import process_document_task

        job_result = process_document_task.delay(str(doc.id), str(organization_id))

        # Record job in DB
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
        """Generate a short-lived signed URL after verifying ownership."""
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
        offset = (page - 1) * page_size
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
            has_next=(offset + page_size) < total,
        )

    async def delete(
        self,
        document_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        doc = await self.docs.get_by_id(document_id, organization_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from storage first (best-effort; don't fail if already gone)
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
