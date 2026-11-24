"""
Abstract AI provider interface.
All AI extraction calls go through this — never call a provider SDK directly from services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractionResult:
    extracted_data: dict[str, Any]
    confidence_scores: dict[str, float]
    overall_confidence: float
    model_used: str
    provider: str
    tokens_used: int | None
    processing_time_ms: int | None


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
        """Return a document type classification string."""
        ...
