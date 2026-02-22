"""
Retry utilities with exponential backoff for Pinecone Assistant MCP.

This module provides decorators and utilities for implementing retry logic
with exponential backoff for transient failures.
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, TypeVar, Tuple, Type

try:
    from ..util.exceptions import RateLimitError, TimeoutError, ServerError
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from util.exceptions import RateLimitError, TimeoutError, ServerError
    from util.secure_logging import setup_secure_logging

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)

T = TypeVar('T')

# Exceptions that should trigger a retry
RETRIABLE_EXCEPTIONS = (
    RateLimitError,
    TimeoutError,
    ServerError,
    ConnectionError,
    OSError,
)


def calculate_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    backoff_factor: float,
    jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Exponential factor (usually 2.0)
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    # Calculate exponential delay
    delay = min(base_delay * (backoff_factor ** attempt), max_delay)

    # Add jitter to prevent thundering herd
    if jitter:
        delay *= (0.5 + random.random() * 0.5)

    return delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff factor
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
                        break

                    # Calculate backoff delay
                    delay = calculate_backoff_delay(
                        attempt, base_delay, max_delay, backoff_factor
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}, "
                        f"retrying in {delay:.2f}s: {type(e).__name__}"
                    )

                    time.sleep(delay)
                except Exception as e:
                    # Don't retry on non-retriable exceptions
                    logger.error(f"Non-retriable error in {func.__name__}: {e}")
                    raise

            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
                        break

                    # Calculate backoff delay
                    delay = calculate_backoff_delay(
                        attempt, base_delay, max_delay, backoff_factor
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}, "
                        f"retrying in {delay:.2f}s: {type(e).__name__}"
                    )

                    await asyncio.sleep(delay)
                except Exception as e:
                    # Don't retry on non-retriable exceptions
                    logger.error(f"Non-retriable error in {func.__name__}: {e}")
                    raise

            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class RetryExecutor:
    """
    Retry executor for manual retry control.

    Use this when you need more control over retry logic than decorators provide.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retry_on: Tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS
    ):
        """
        Initialize retry executor.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Exponential backoff factor
            retry_on: Tuple of exception types to retry on
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retry_on as e:
                last_exception = e

                if attempt == self.max_retries:
                    break

                delay = calculate_backoff_delay(
                    attempt,
                    self.base_delay,
                    self.max_delay,
                    self.backoff_factor
                )

                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries + 1} after {delay:.2f}s: {type(e).__name__}"
                )

                time.sleep(delay)
            except Exception as e:
                logger.error(f"Non-retriable error: {e}")
                raise

        if last_exception:
            raise last_exception

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.retry_on as e:
                last_exception = e

                if attempt == self.max_retries:
                    break

                delay = calculate_backoff_delay(
                    attempt,
                    self.base_delay,
                    self.max_delay,
                    self.backoff_factor
                )

                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries + 1} after {delay:.2f}s: {type(e).__name__}"
                )

                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Non-retriable error: {e}")
                raise

        if last_exception:
            raise last_exception


# Aliases for backward compatibility with tests
exponential_backoff = calculate_backoff_delay
RetryableHTTPClient = RetryExecutor
