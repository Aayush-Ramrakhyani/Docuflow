"""
AI provider factory.

Centralizes provider selection behind get_ai_provider() so the rest of the app
depends on the abstract AIProvider interface, never a concrete SDK. Swapping or
A/B-testing providers later means changing only this function.
"""

from app.services.ai.base import AIProvider, ExtractionResult
from app.services.ai.anthropic_provider import AnthropicProvider


def get_ai_provider() -> AIProvider:
    # Single place to change which provider the whole app uses
    return AnthropicProvider()
