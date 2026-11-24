"""Document upload and response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    page_count: int | None
    document_type: str | None
    status: str
    status_message: str | None
    created_at: str  # ISO8601
    updated_at: str  # ISO8601

    class Config:
        json_encoders = {
            "datetime": lambda v: v.isoformat(),
        }


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job_id: UUID


class UpdateDocumentRequest(BaseModel):
    document_type: str | None = Field(default=None, max_length=100)


class DocumentFilterParams(BaseModel):
    status: str | None = None
    document_type: str | None = None
    search: str | None = Field(default=None, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int  # seconds
