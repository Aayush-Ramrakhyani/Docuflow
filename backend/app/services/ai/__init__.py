from app.services.ai.base import AIProvider, ExtractionResult
from app.services.ai.anthropic_provider import AnthropicProvider


def get_ai_provider() -> AIProvider:
    return AnthropicProvider()
