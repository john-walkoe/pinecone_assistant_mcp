"""
Pydantic data models for Pinecone Assistant MCP.

Type-safe data models for request validation, response parsing, and
configuration management. All models include comprehensive validation
and serialization support.

Model Categories:
    - Request Models: AssistantChatParams, AssistantContextParams
    - Strategic Search: StrategySearchParams, StrategyContextParams
    - Configuration: SearchPattern, SearchDomain
    - Response Models: ContextSnippet, AssistantContextResponse, Message

All models support:
    - JSON serialization/deserialization
    - Field validation with Pydantic V2
    - Type hints for IDE support
    - Automatic API documentation generation
"""

from .models import (
    Message,
    AssistantChatParams,
    AssistantContextParams,
    StrategySearchParams,
    StrategyContextParams,
    SearchPattern,
    SearchDomain,
    ContextSnippet,
    AssistantContextResponse,
)

__all__ = [
    "Message",
    "AssistantChatParams",
    "AssistantContextParams",
    "StrategySearchParams",
    "StrategyContextParams",
    "SearchPattern",
    "SearchDomain",
    "ContextSnippet",
    "AssistantContextResponse",
]
