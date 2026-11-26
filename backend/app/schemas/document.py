"""
Document request/response schemas.

Response models are built straight from ORM objects (from_attributes). List
responses carry pagination metadata so the client can render page controls.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}  # Build from a SQLAlchemy Document

    id: UUID
    organization_id: UUID
    original_filename: str          # Display name only — never a filesystem path
    file_size_bytes: int
    mime_type: str                  # Server-detected type, not the client's claim
    page_count: int | None
    document_type: str | None       # Set by AI classification after processing
    status: str                     # Lifecycle: uploaded → queued → processing → review_pending → …
    status_message: str | None
    created_at: str                 # ISO8601 timestamp
    updated_at: str                 # ISO8601 timestamp

    class Config:
        json_encoders = {
            "datetime": lambda v: v.isoformat(),
        }


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int          # Total matching rows (across all pages)
    page: int
    page_size: int
    has_next: bool      # True when another page exists


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job_id: UUID        # Processing job id — client polls this for status


class UpdateDocumentRequest(BaseModel):
    document_type: str | None = Field(default=None, max_length=100)


class DocumentFilterParams(BaseModel):
    status: str | None = None
    document_type: str | None = None
    search: str | None = Field(default=None, max_length=255)  # Capped to bound the ILIKE
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)          # Hard upper bound on page size


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int  # Seconds until the signed URL stops working
