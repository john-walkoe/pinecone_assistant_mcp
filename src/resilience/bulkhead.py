"""
Bulkhead pattern implementation for Pinecone Assistant MCP.

This module implements the bulkhead pattern to isolate resources and prevent
failure in one component from affecting others.
"""

import asyncio
import logging
import time
from typing import Callable, TypeVar, Optional
from functools import wraps
from threading import Semaphore, Lock

try:
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from util.secure_logging import setup_secure_logging

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)

T = TypeVar('T')


class Bulkhead:
    """
    Bulkhead for limiting concurrent operations.

    The bulkhead pattern isolates resources to prevent a failure in one
    component from cascading to others. It works by limiting the number
    of concurrent operations.
    """

    def __init__(
        self,
        name: str = "default",
        max_concurrent: int = 10,
        max_wait_time: float = 30.0
    ):
        """
        Initialize bulkhead.

        Args:
            name: Bulkhead name for logging
            max_concurrent: Maximum concurrent operations allowed
            max_wait_time: Maximum time to wait for a slot (seconds)
        """
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_wait_time = max_wait_time

        self._semaphore = Semaphore(max_concurrent)
        self._async_semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = Lock()

        self._active_count = 0
        self._total_executions = 0
        self._total_rejections = 0
        self._total_wait_time = 0.0

        logger.info(
            f"Bulkhead '{name}' initialized with max_concurrent={max_concurrent}, "
            f"max_wait_time={max_wait_time}s"
        )

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function within the bulkhead.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RuntimeError: If unable to acquire slot within max_wait_time
        """
        wait_start = time.time()

        # Try to acquire semaphore with timeout
        acquired = self._semaphore.acquire(timeout=self.max_wait_time)

        if not acquired:
            wait_time = time.time() - wait_start
            with self._lock:
                self._total_rejections += 1

            logger.warning(
                f"Bulkhead '{self.name}' rejected request after {wait_time:.2f}s wait "
                f"(max_concurrent={self.max_concurrent} reached)"
            )
            raise RuntimeError(
                f"Bulkhead '{self.name}' is full. "
                f"Maximum concurrent operations ({self.max_concurrent}) reached."
            )

        wait_time = time.time() - wait_start

        try:
            with self._lock:
                self._active_count += 1
                self._total_executions += 1
                self._total_wait_time += wait_time

            if wait_time > 0.1:  # Log if we waited more than 100ms
                logger.debug(
                    f"Bulkhead '{self.name}' acquired after {wait_time:.2f}s wait "
                    f"({self._active_count}/{self.max_concurrent} active)"
                )

            return func(*args, **kwargs)
        finally:
            with self._lock:
                self._active_count -= 1
            self._semaphore.release()

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function within the bulkhead.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RuntimeError: If unable to acquire slot within max_wait_time
        """
        wait_start = time.time()

        try:
            # Try to acquire with timeout
            await asyncio.wait_for(
                self._async_semaphore.acquire(),
                timeout=self.max_wait_time
            )
        except asyncio.TimeoutError:
            wait_time = time.time() - wait_start
            with self._lock:
                self._total_rejections += 1

            logger.warning(
                f"Bulkhead '{self.name}' rejected async request after {wait_time:.2f}s wait "
                f"(max_concurrent={self.max_concurrent} reached)"
            )
            raise RuntimeError(
                f"Bulkhead '{self.name}' is full. "
                f"Maximum concurrent operations ({self.max_concurrent}) reached."
            )

        wait_time = time.time() - wait_start

        try:
            with self._lock:
                self._active_count += 1
                self._total_executions += 1
                self._total_wait_time += wait_time

            if wait_time > 0.1:
                logger.debug(
                    f"Bulkhead '{self.name}' acquired after {wait_time:.2f}s wait "
                    f"({self._active_count}/{self.max_concurrent} active)"
                )

            return await func(*args, **kwargs)
        finally:
            with self._lock:
                self._active_count -= 1
            self._async_semaphore.release()

    def get_stats(self) -> dict:
        """
        Get bulkhead statistics.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            avg_wait_time = (
                self._total_wait_time / self._total_executions
                if self._total_executions > 0
                else 0.0
            )

            return {
                "name": self.name,
                "max_concurrent": self.max_concurrent,
                "active_count": self._active_count,
                "total_executions": self._total_executions,
                "total_rejections": self._total_rejections,
                "avg_wait_time": round(avg_wait_time, 3),
                "utilization": round(
                    (self._active_count / self.max_concurrent * 100), 2
                )
            }


def bulkhead(
    name: str = "default",
    max_concurrent: int = 10,
    max_wait_time: float = 30.0
):
    """
    Decorator to wrap a function with bulkhead protection.

    Args:
        name: Bulkhead name for logging
        max_concurrent: Maximum concurrent operations
        max_wait_time: Maximum wait time for a slot

    Returns:
        Decorated function with bulkhead
    """
    bulkhead_instance = Bulkhead(
        name=name,
        max_concurrent=max_concurrent,
        max_wait_time=max_wait_time
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return bulkhead_instance.execute(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await bulkhead_instance.execute_async(func, *args, **kwargs)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class BulkheadRegistry:
    """
    Registry for managing multiple bulkheads.

    Use this to coordinate resource isolation across your application.
    """

    def __init__(self):
        """Initialize the registry."""
        self._bulkheads: dict[str, Bulkhead] = {}

    def get_or_create(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_time: float = 30.0
    ) -> Bulkhead:
        """
        Get existing bulkhead or create a new one.

        Args:
            name: Bulkhead name
            max_concurrent: Maximum concurrent operations
            max_wait_time: Maximum wait time

        Returns:
            Bulkhead instance
        """
        if name not in self._bulkheads:
            self._bulkheads[name] = Bulkhead(
                name=name,
                max_concurrent=max_concurrent,
                max_wait_time=max_wait_time
            )
        return self._bulkheads[name]

    def get_stats_all(self) -> dict[str, dict]:
        """
        Get stats for all bulkheads.

        Returns:
            Dictionary mapping names to stats
        """
        return {name: bh.get_stats() for name, bh in self._bulkheads.items()}


# Alias for backward compatibility with tests
BulkheadIsolator = Bulkhead
