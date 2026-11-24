"""
Celery worker: document OCR + AI extraction pipeline.
Runs asynchronously — API returns immediately after upload.

Performance notes:
- Event loop is created once per worker process and reused across tasks.
- StorageService uses a module-level boto3 singleton — no per-task client creation.
- DB sessions consolidated to 2 per pipeline (init + finalize) instead of 5.
"""

import asyncio
import uuid
from datetime import UTC, datetime

import fitz  # PyMuPDF
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.core.celery_app import celery_app
from app.core.database import rls_session
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.job import ProcessingJob
from app.services.ai import get_ai_provider
from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)

# Reuse one event loop per Celery worker process instead of creating per task
_worker_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def _extract_text_from_pdf_bytes(content: bytes) -> tuple[str, int]:
    """Extract text from PDF bytes. Returns (text, page_count)."""
    doc = fitz.open(stream=content, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages), len(pages)


# Only retry transient infrastructure errors — not ValueError/JSONDecodeError etc.
_RETRIABLE = (BotoCoreError, ClientError, ConnectionError, TimeoutError, OSError)


@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=_RETRIABLE,
    retry_backoff=True,
)
def process_document_task(self, document_id: str, organization_id: str) -> dict:
    """
    Full document processing pipeline:
    1. Mark running in DB
    2. Download from S3
    3. Extract text (PDF text layer or OCR fallback)
    4. Classify document type (AI)
    5. AI extraction
    6. Store extraction result + finalize document status
    """
    return _get_worker_loop().run_until_complete(
        _process_document_async(document_id, organization_id, self)
    )


async def _process_document_async(
    document_id: str, organization_id: str, task
) -> dict:
    doc_uuid = uuid.UUID(document_id)
    org_uuid = uuid.UUID(organization_id)
    storage = StorageService()
    ai = get_ai_provider()

    # ── Session 1: mark running, fetch document record ────────────────────────
    storage_key: str
    storage_bucket: str
    mime_type: str

    async with rls_session(organization_id) as db:
        from sqlalchemy import select, update

        await db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.document_id == doc_uuid,
                ProcessingJob.celery_task_id == task.request.id,
            )
            .values(status="running", started_at=datetime.now(UTC))
        )
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(status="processing")
        )

        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        storage_key = doc.storage_key
        storage_bucket = doc.storage_bucket
        mime_type = doc.mime_type
        await db.commit()

    # ── CPU/IO work outside any DB session ───────────────────────────────────
    try:
        content = storage.download_file(storage_bucket, storage_key)

        if mime_type == "application/pdf":
            document_text, page_count = _extract_text_from_pdf_bytes(content)
        else:
            # Images: placeholder — OCR (Tesseract/AWS Textract) would go here
            document_text = "[Image content — OCR not yet implemented]"
            page_count = 1

        # Both AI calls happen here, outside DB sessions
        doc_type = await ai.classify_document(document_text)
        extraction_result = await ai.extract_document(
            document_text=document_text,
            document_type=doc_type,
        )

    except Exception as exc:
        await _mark_failed(doc_uuid, task.request.id, organization_id, str(exc))
        raise

    # ── Session 2: persist all results in one transaction ────────────────────
    async with rls_session(organization_id) as db:
        from sqlalchemy import update

        extraction = Extraction(
            document_id=doc_uuid,
            organization_id=org_uuid,
            model_used=extraction_result.model_used,
            provider=extraction_result.provider,
            extracted_data=extraction_result.extracted_data,
            confidence_scores=extraction_result.confidence_scores,
            overall_confidence=extraction_result.overall_confidence,
            tokens_used=extraction_result.tokens_used,
            processing_time_ms=extraction_result.processing_time_ms,
        )
        db.add(extraction)

        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(
                status="review_pending",
                page_count=page_count,
                document_type=doc_type,
            )
        )
        await db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.document_id == doc_uuid,
                ProcessingJob.celery_task_id == task.request.id,
            )
            .values(
                status="completed",
                completed_at=datetime.now(UTC),
                result_summary={
                    "document_type": doc_type,
                    "fields_extracted": len(extraction_result.extracted_data),
                    "overall_confidence": extraction_result.overall_confidence,
                },
            )
        )
        await db.commit()

    logger.info(
        "document_processed",
        document_id=document_id,
        doc_type=doc_type,
        fields=len(extraction_result.extracted_data),
    )
    return {"status": "completed", "document_id": document_id}


async def _mark_failed(
    doc_uuid: uuid.UUID,
    celery_task_id: str,
    organization_id: str,
    error_msg: str,
) -> None:
    """Write failed status to DB without raising (best-effort)."""
    try:
        async with rls_session(organization_id) as db:
            from sqlalchemy import update

            await db.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(status="failed", status_message=error_msg[:500])
            )
            await db.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.document_id == doc_uuid,
                    ProcessingJob.celery_task_id == celery_task_id,
                )
                .values(
                    status="failed",
                    failed_at=datetime.now(UTC),
                    error_message=error_msg[:500],
                )
            )
            await db.commit()
    except Exception:
        logger.exception("failed_to_mark_document_failed", document_id=str(doc_uuid))
