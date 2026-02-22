"""
Pinecone Assistant MCP Server.

A Model Context Protocol (MCP) server providing AI-powered document research
capabilities using the Pinecone Assistant API. This generic, domain-agnostic
architecture supports any document corpus with customizable search patterns.

The USPTO patent examination use case serves as a reference implementation,
demonstrating strategic search patterns and multi-query orchestration for
complex research workflows.

Key Features:
    - Zero-token-cost document retrieval via semantic search
    - AI-powered chat with RAG (Retrieval Augmented Generation)
    - Strategic multi-search workflows with YAML configuration
    - Six supported AI models (GPT, Claude, Gemini)
    - Comprehensive security and fault tolerance patterns

Version: 1.0.0
API Version: 2025-04
License: MIT
"""

__version__ = "1.0.0"