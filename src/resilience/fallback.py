"""
Graceful degradation and fallback mechanisms for Pinecone Assistant MCP.

This module provides utilities for implementing fallback behavior when
operations fail, allowing the system to degrade gracefully.
"""

import logging
from typing import Callable, TypeVar, Optional, List, Any

try:
    from ..util.exceptions import RateLimitError, ResourceNotFoundError
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from util.exceptions import RateLimitError, ResourceNotFoundError
    from util.secure_logging import setup_secure_logging

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)

T = TypeVar('T')


class FallbackChain:
    """
    Execute a chain of fallback operations.

    This class tries multiple operations in sequence until one succeeds,
    allowing for graceful degradation of functionality.
    """

    def __init__(self, name: str = "default"):
        """
        Initialize fallback chain.

        Args:
            name: Name for logging
        """
        self.name = name
        self.operations: List[Callable] = []
        self.operation_names: List[str] = []

    def add_fallback(self, operation: Callable, name: str = None):
        """
        Add a fallback operation to the chain.

        Args:
            operation: Callable to execute
            name: Optional name for logging
        """
        self.operations.append(operation)
        self.operation_names.append(name or f"fallback_{len(self.operations)}")
        return self

    def execute(self, *args, **kwargs) -> T:
        """
        Execute the fallback chain.

        Args:
            *args: Positional arguments for operations
            **kwargs: Keyword arguments for operations

        Returns:
            Result from first successful operation

        Raises:
            RuntimeError: If all operations fail
        """
        last_exception = None
        errors = []

        for operation, op_name in zip(self.operations, self.operation_names):
            try:
                logger.debug(f"Fallback chain '{self.name}' trying: {op_name}")
                result = operation(*args, **kwargs)
                logger.info(f"Fallback chain '{self.name}' succeeded with: {op_name}")
                return result
            except Exception as e:
                last_exception = e
                errors.append((op_name, str(e)))
                logger.warning(f"Fallback '{op_name}' failed: {e}")

        # All fallbacks failed
        error_summary = "; ".join([f"{name}: {err}" for name, err in errors])
        logger.error(
            f"All fallbacks failed in chain '{self.name}': {error_summary}"
        )
        raise RuntimeError(
            f"All fallback operations failed in chain '{self.name}'. "
            f"Last error: {last_exception}"
        )


class ContextRetrievalFallback:
    """
    Specialized fallback for context retrieval operations.

    Provides strategies for degrading context retrieval when the primary
    method fails.
    """

    @staticmethod
    def with_reduced_parameters(client, params):
        """
        Fallback that retries with reduced parameters.

        Args:
            client: Assistant client
            params: Original context parameters

        Returns:
            Context results with reduced parameters
        """
        logger.info("Attempting context retrieval with reduced parameters")

        # Create reduced params
        reduced_params = params.copy() if hasattr(params, 'copy') else params

        # Reduce top_k
        if hasattr(reduced_params, 'top_k'):
            original_top_k = reduced_params.top_k
            reduced_params.top_k = min(reduced_params.top_k, 3)
            logger.debug(f"Reduced top_k from {original_top_k} to {reduced_params.top_k}")

        # Reduce snippet_size
        if hasattr(reduced_params, 'snippet_size'):
            original_size = reduced_params.snippet_size
            reduced_params.snippet_size = min(reduced_params.snippet_size, 1024)
            logger.debug(f"Reduced snippet_size from {original_size} to {reduced_params.snippet_size}")

        return client.context(reduced_params)

    @staticmethod
    def with_error_response(error: Exception):
        """
        Create an error response when all retrieval attempts fail.

        Args:
            error: The exception that caused the failure

        Returns:
            Error response dictionary
        """
        logger.warning("Creating error response for failed context retrieval")

        return {
            "error": True,
            "message": "Context retrieval temporarily unavailable",
            "snippets": [],
            "suggestion": (
                "The system is experiencing issues retrieving document context. "
                "Please try again in a moment or use the assistant_chat tool instead."
            ),
            "original_error": type(error).__name__
        }


class ChatFallback:
    """
    Specialized fallback for chat operations.

    Provides strategies for degrading chat functionality when needed.
    """

    @staticmethod
    def with_simplified_model(client, params, fallback_model: str = "gpt-4o"):
        """
        Fallback that retries with a simpler/faster model.

        Args:
            client: Assistant client
            params: Original chat parameters
            fallback_model: Model to use as fallback

        Returns:
            Chat results with fallback model
        """
        logger.info(f"Attempting chat with fallback model: {fallback_model}")

        # Create params with fallback model
        fallback_params = params.copy() if hasattr(params, 'copy') else params

        if hasattr(fallback_params, 'model'):
            original_model = fallback_params.model
            fallback_params.model = fallback_model
            logger.debug(f"Changed model from {original_model} to {fallback_model}")

        return client.chat(fallback_params)

    @staticmethod
    def with_shorter_context(client, params):
        """
        Fallback that retries with shorter message history.

        Args:
            client: Assistant client
            params: Original chat parameters

        Returns:
            Chat results with reduced context
        """
        logger.info("Attempting chat with shortened context")

        # Create params with only recent messages
        shortened_params = params.copy() if hasattr(params, 'copy') else params

        if hasattr(shortened_params, 'messages') and len(shortened_params.messages) > 2:
            original_count = len(shortened_params.messages)
            # Keep only the last 2 messages
            shortened_params.messages = shortened_params.messages[-2:]
            logger.debug(f"Reduced message count from {original_count} to {len(shortened_params.messages)}")

        return client.chat(shortened_params)

    @staticmethod
    def with_error_response(error: Exception):
        """
        Create an error response when all chat attempts fail.

        Args:
            error: The exception that caused the failure

        Returns:
            Error response dictionary
        """
        logger.warning("Creating error response for failed chat")

        return {
            "error": True,
            "message": {
                "role": "assistant",
                "content": (
                    "I apologize, but I'm experiencing technical difficulties and "
                    "cannot process your request at the moment. Please try again in a few moments."
                )
            },
            "suggestion": (
                "The chat service is temporarily unavailable. "
                "You can try using the assistant_context tool for document retrieval instead."
            ),
            "original_error": type(error).__name__
        }


def create_context_fallback_chain(client, params) -> FallbackChain:
    """
    Create a fallback chain for context retrieval.

    Args:
        client: Assistant client
        params: Context parameters

    Returns:
        Configured fallback chain
    """
    chain = FallbackChain(name="context_retrieval")

    # Primary: Try with original parameters
    chain.add_fallback(
        lambda: client.context(params),
        name="primary_context"
    )

    # Fallback 1: Try with reduced parameters
    chain.add_fallback(
        lambda: ContextRetrievalFallback.with_reduced_parameters(client, params),
        name="reduced_parameters"
    )

    return chain


def create_chat_fallback_chain(client, params) -> FallbackChain:
    """
    Create a fallback chain for chat operations.

    Args:
        client: Assistant client
        params: Chat parameters

    Returns:
        Configured fallback chain
    """
    chain = FallbackChain(name="chat")

    # Primary: Try with original parameters
    chain.add_fallback(
        lambda: client.chat(params),
        name="primary_chat"
    )

    # Fallback 1: Try with simpler model
    chain.add_fallback(
        lambda: ChatFallback.with_simplified_model(client, params),
        name="simplified_model"
    )

    # Fallback 2: Try with shorter context
    chain.add_fallback(
        lambda: ChatFallback.with_shorter_context(client, params),
        name="shortened_context"
    )

    return chain


def safe_execute_with_fallback(
    primary_operation: Callable[[], T],
    fallback_operation: Optional[Callable[[], T]] = None,
    error_handler: Optional[Callable[[Exception], T]] = None
) -> T:
    """
    Execute an operation with a single fallback and error handling.

    Args:
        primary_operation: Primary operation to attempt
        fallback_operation: Optional fallback if primary fails
        error_handler: Optional error handler if both fail

    Returns:
        Result from successful operation

    Raises:
        Exception from primary if no fallback/handler provided
    """
    try:
        return primary_operation()
    except Exception as e:
        logger.warning(f"Primary operation failed: {e}")

        if fallback_operation:
            try:
                logger.info("Attempting fallback operation")
                return fallback_operation()
            except Exception as fallback_error:
                logger.error(f"Fallback operation also failed: {fallback_error}")

                if error_handler:
                    return error_handler(e)
                raise

        if error_handler:
            return error_handler(e)
        raise


# Alias for backward compatibility with tests
FallbackStrategy = FallbackChain
