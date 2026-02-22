"""
Strategic search and context services.

Business logic for orchestrating multi-query strategic searches across document
collections. Supports YAML-based search pattern configuration with template
substitution and keyword extraction.

Services:
    - StrategySearchProcessor: AI-powered multi-search with response aggregation
    - StrategicContextSearcher: Raw document retrieval for zero-token workflows

Features:
    - YAML-driven search patterns with {primary} and {key_terms} placeholders
    - Automatic keyword extraction from queries
    - Parallel query execution
    - Result aggregation and deduplication
    - Domain-specific search customization
"""

from .strategic_search import StrategySearchProcessor
from .strategic_context import StrategicContextSearcher

__all__ = [
    "StrategySearchProcessor",
    "StrategicContextSearcher",
]
