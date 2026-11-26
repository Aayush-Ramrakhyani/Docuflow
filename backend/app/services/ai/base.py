"""
Abstract AI provider interface.

All AI extraction/classification flows through this contract — services and
workers depend on AIProvider, never on a vendor SDK directly. This keeps prompt
handling, injection defenses, and provider swaps isolated to the implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractionResult:
    """Normalized result every provider must return, regardless of vendor shape."""
    extracted_data: dict[str, Any]          # The structured fields pulled from the document
    confidence_scores: dict[str, float]     # Per-field confidence, 0.0–1.0, for the review UI
    overall_confidence: float               # Single document-level confidence, 0.0–1.0
    model_used: str                         # Exact model id (for audit/repro)
    provider: str                           # e.g. "anthropic"
    tokens_used: int | None                 # For cost tracking
    processing_time_ms: int | None          # For performance tracking


class AIProvider(ABC):
    @abstractmethod
    async def extract_document(
        self,
        document_text: str,
        document_type: str | None = None,
        schema_hint: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """
        Extract structured data from document text.
        document_text must be pre-processed (OCR result or PDF text layer).
        """
        ...

    @abstractmethod
    async def classify_document(self, document_text: str) -> str:
        """Return a document type classification string (e.g. "invoice")."""
        ...
