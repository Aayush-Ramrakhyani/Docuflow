"""
Shared response envelopes reused across the API.

Generic wrappers (SuccessResponse, PaginatedResponse) and the standard error
shape live here so every endpoint returns a consistent structure to clients.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")  # Generic payload type for the envelopes below


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T  # Whatever resource the endpoint returns


class ErrorDetail(BaseModel):
    field: str | None = None  # Which input field failed (None = non-field error)
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str                                  # Human-readable summary
    details: list[ErrorDetail] | None = None    # Per-field validation errors, when applicable
    request_id: str | None = None               # Correlates with server logs for debugging


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class MessageResponse(BaseModel):
    message: str  # Simple {"message": "..."} ack for actions with no resource to return
