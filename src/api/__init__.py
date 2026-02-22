"""
Pinecone Assistant API client module.

Provides HTTP client implementations for interacting with the Pinecone Assistant API.
Includes connection pooling, error handling, and response serialization.

Classes:
    - PineconeAssistantClient: Main client for chat and context operations
    - AssistantClientManager: Singleton manager with connection pooling

Usage:
    >>> from src.api import AssistantClientManager
    >>> client = AssistantClientManager.get_client(settings)
    >>> response = client.chat(params)
"""

from .assistant_client import (
    PineconeAssistantClient,
    AssistantClientManager,
)

__all__ = [
    "PineconeAssistantClient",
    "AssistantClientManager",
]
