"""
Extraction review/correction schemas.

These back the human-in-the-loop workspace: the response exposes per-field
confidence and both the raw + corrected data, while the request models validate
reviewer actions (correct / approve / reject).
"""

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
    extracted_data: dict[str, Any]          # Raw AI output
    confidence_scores: dict[str, float]     # Per-field confidence — drives the review UI colors
    overall_confidence: float | None
    corrected_data: dict[str, Any] | None   # Reviewer edits, kept separate from the AI output
    final_data: dict[str, Any]              # Computed: corrected values merged over extracted
    status: str
    reviewed_by_id: UUID | None
    reviewed_at: str | None
    review_notes: str | None
    tokens_used: int | None
    processing_time_ms: int | None
    created_at: str
    updated_at: str


class CorrectExtractionRequest(BaseModel):
    """Partial correction: only include the fields that need changing."""
    corrections: dict[str, Any] = Field(min_length=1)       # Must correct at least one field
    notes: str | None = Field(default=None, max_length=1000)


class ApproveExtractionRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)  # Optional sign-off note


class RejectExtractionRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=1000)  # Required — a rejection must state why


class ExtractionListResponse(BaseModel):
    items: list[ExtractionResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
