"""Extraction review and correction schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    document_id: UUID
    organization_id: UUID
    model_used: str
    provider: str
    extracted_data: dict[str, Any]
    confidence_scores: dict[str, float]
    overall_confidence: float | None
    corrected_data: dict[str, Any] | None
    final_data: dict[str, Any]
    status: str
    reviewed_by_id: UUID | None
    reviewed_at: str | None
    review_notes: str | None
    tokens_used: int | None
    processing_time_ms: int | None
    created_at: str
    updated_at: str


class CorrectExtractionRequest(BaseModel):
    """Partial correction: only specify fields that need changing."""
    corrections: dict[str, Any] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class ApproveExtractionRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class RejectExtractionRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=1000)


class ExtractionListResponse(BaseModel):
    items: list[ExtractionResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
