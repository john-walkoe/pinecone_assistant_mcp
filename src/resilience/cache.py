"""
Response caching for Pinecone Assistant MCP.

This module provides in-memory caching to reduce API calls and improve performance.
"""

import hashlib
import json
import logging
import time
from typing import Any, Optional, Callable
from functools import wraps

try:
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from util.secure_logging import setup_secure_logging

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)


class CacheEntry:
    """A single cache entry with expiration."""

    def __init__(self, value: Any, ttl: float):
        """
        Initialize cache entry.

        Args:
            value: Cached value
            ttl: Time-to-live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl == 0:
            return False  # Never expires
        return (time.time() - self.created_at) > self.ttl


class ResponseCache:
    """
    Simple in-memory cache for API responses.

    This cache is useful for reducing repeated API calls for identical queries.
    It's particularly helpful for context retrieval where users might ask the
    same question multiple times.
    """

    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000):
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds (5 minutes default)
            max_size: Maximum number of entries before eviction
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """
        Create a cache key from function arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a stable representation of the arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache miss (expired): {key[:16]}...")
            return None

        self._hits += 1
        logger.debug(f"Cache hit: {key[:16]}...")
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        # Evict oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        ttl = ttl if ttl is not None else self.default_ttl
        self._cache[key] = CacheEntry(value, ttl)
        logger.debug(f"Cache set: {key[:16]}... (ttl={ttl}s)")

    def _evict_oldest(self):
        """Evict the oldest cache entry."""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        del self._cache[oldest_key]
        logger.debug(f"Evicted oldest cache entry: {oldest_key[:16]}...")

    def invalidate(self, key: str):
        """
        Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key[:16]}...")

    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info(f"Cache cleared ({count} entries removed)")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests
        }


def cached(
    cache: ResponseCache,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator to cache function results.

    Args:
        cache: ResponseCache instance to use
        ttl: Time-to-live for cached results (uses cache default if None)
        key_func: Optional function to generate cache key from arguments

    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._make_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


class ContextCache(ResponseCache):
    """
    Specialized cache for context retrieval.

    This cache is optimized for storing document context snippets.
    """

    def __init__(self, default_ttl: float = 600.0, max_size: int = 500):
        """
        Initialize context cache.

        Args:
            default_ttl: Default TTL (10 minutes for context)
            max_size: Maximum cache size (500 entries)
        """
        super().__init__(default_ttl=default_ttl, max_size=max_size)

    def make_query_key(self, query: str, top_k: int, snippet_size: int) -> str:
        """
        Create a cache key for a context query.

        Args:
            query: Search query
            top_k: Number of results
            snippet_size: Snippet size

        Returns:
            Cache key
        """
        key_data = {
            "query": query.lower().strip(),
            "top_k": top_k,
            "snippet_size": snippet_size
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()


class ChatCache(ResponseCache):
    """
    Specialized cache for chat responses.

    This cache is more conservative with TTL since chat responses
    are more context-dependent.
    """

    def __init__(self, default_ttl: float = 180.0, max_size: int = 200):
        """
        Initialize chat cache.

        Args:
            default_ttl: Default TTL (3 minutes for chat)
            max_size: Maximum cache size (200 entries)
        """
        super().__init__(default_ttl=default_ttl, max_size=max_size)

    def make_message_key(self, messages: list, model: str) -> str:
        """
        Create a cache key for a chat request.

        Args:
            messages: List of message dictionaries
            model: Model name

        Returns:
            Cache key
        """
        # Only use the last user message for caching
        # (full conversation history would make caching less effective)
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        key_data = {
            "message": last_user_message,
            "model": model
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
