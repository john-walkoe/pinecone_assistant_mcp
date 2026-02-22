"""
Error context and correlation ID management for Pinecone Assistant MCP.

This module provides request-scoped error tracking and correlation IDs
for improved debugging and error tracing across the system.
"""

import uuid
import contextvars
import logging
from typing import Optional, Any, Dict
from functools import wraps

try:
    from .secure_logging import setup_secure_logging
except ImportError:
    from secure_logging import setup_secure_logging

logger = setup_secure_logging(__name__, level=logging.INFO)

# Context variable for request-scoped error tracking
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')
_operation_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    'operation_context', default={}
)


def generate_request_id() -> str:
    """Generate a new unique request ID."""
    return uuid.uuid4().hex[:12]


def get_request_id() -> str:
    """
    Get current request ID or create new one if not set.

    Returns:
        12-character hexadecimal request ID
    """
    request_id = _request_id.get()
    if not request_id:
        request_id = generate_request_id()
        _request_id.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """
    Set request ID for current context.

    Args:
        request_id: Request ID to set
    """
    _request_id.set(request_id)


def clear_request_id() -> None:
    """Clear the current request ID."""
    _request_id.set('')


def get_operation_context() -> Dict[str, Any]:
    """Get current operation context."""
    return _operation_context.get()


def set_operation_context(**kwargs) -> None:
    """
    Set operation context metadata.

    Args:
        **kwargs: Key-value pairs to add to context
    """
    current = _operation_context.get().copy()
    current.update(kwargs)
    _operation_context.set(current)


def clear_operation_context() -> None:
    """Clear the operation context."""
    _operation_context.set({})


class ErrorContext:
    """
    Context manager for error tracking with correlation IDs.

    Automatically logs errors with request ID and operation context.
    """

    def __init__(self, operation: str, **metadata):
        """
        Initialize error context.

        Args:
            operation: Name of the operation being performed
            **metadata: Additional metadata to include in logs
        """
        self.operation = operation
        # Extract request_id from metadata if provided, otherwise generate new one
        self.request_id = metadata.pop('request_id', None) or get_request_id()
        self.metadata = metadata
        self.token = None

    def __enter__(self):
        """Enter context and set operation metadata."""
        # Store current context and update
        set_operation_context(
            operation=self.operation,
            request_id=self.request_id,
            **self.metadata
        )
        logger.debug(f"[{self.request_id}] Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context and log any errors.

        Returns:
            False to propagate exceptions
        """
        if exc_type:
            # Log error with full context
            logger.error(
                f"[{self.request_id}] Error in {self.operation}: {exc_val}",
                extra={
                    'request_id': self.request_id,
                    'operation': self.operation,
                    'error_type': exc_type.__name__,
                    **self.metadata
                }
            )
        else:
            logger.debug(f"[{self.request_id}] Completed operation: {self.operation}")

        return False  # Don't suppress exceptions

    def add_metadata(self, **kwargs):
        """Add additional metadata to the context."""
        self.metadata.update(kwargs)
        set_operation_context(**kwargs)


def with_error_context(operation: str):
    """
    Decorator to wrap a function with error context.

    Args:
        operation: Name of the operation

    Returns:
        Decorated function with error tracking
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorContext(operation):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with ErrorContext(operation):
                return await func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def format_error_response(
    error: Exception,
    include_request_id: bool = True,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Format an error into a structured response.

    Args:
        error: The exception to format
        include_request_id: Whether to include request ID
        include_details: Whether to include technical details

    Returns:
        Structured error response dictionary
    """
    request_id = get_request_id() if include_request_id else None

    # Extract error code if available
    error_code = getattr(error, 'error_code', 'INTERNAL_ERROR')

    # Determine if error is recoverable
    recoverable = error_code in [
        'RATE_LIMIT', 'TIMEOUT', 'SERVER_ERROR',
        'BAD_GATEWAY', 'SERVICE_UNAVAILABLE', 'GATEWAY_TIMEOUT'
    ]

    response = {
        "error": True,
        "code": error_code,
        "message": str(error),
        "recoverable": recoverable
    }

    if include_request_id and request_id:
        response["request_id"] = request_id

    if include_details:
        response["details"] = {
            "type": type(error).__name__,
            "context": get_operation_context()
        }

    # Add retry hint for recoverable errors
    if error_code == 'RATE_LIMIT':
        response["retry_after"] = 60
    elif error_code in ['TIMEOUT', 'SERVER_ERROR', 'BAD_GATEWAY', 'SERVICE_UNAVAILABLE']:
        response["retry_after"] = 30

    return response


class RequestScope:
    """
    Context manager for request-scoped operations.

    Automatically manages request ID lifecycle.
    """

    def __init__(self, request_id: Optional[str] = None):
        """
        Initialize request scope.

        Args:
            request_id: Optional request ID (generated if not provided)
        """
        self.request_id = request_id or generate_request_id()
        self.token = None

    def __enter__(self):
        """Enter request scope and set request ID."""
        self.token = _request_id.set(self.request_id)
        clear_operation_context()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit request scope and clean up."""
        if self.token:
            _request_id.reset(self.token)
        clear_operation_context()
        return False
