"""
Custom exception hierarchy for Pinecone Assistant MCP.

This module defines application-specific exceptions that provide better
error categorization and handling throughout the codebase.
"""


class PineconeAssistantError(Exception):
    """Base exception for all Pinecone Assistant MCP errors."""

    def __init__(self, message: str, error_code: str = None):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
        """
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(PineconeAssistantError):
    """Raised when authentication fails (401 Unauthorized)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_FAILED")


class AuthorizationError(PineconeAssistantError):
    """Raised when authorization fails (403 Forbidden)."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, error_code="ACCESS_FORBIDDEN")


class ResourceNotFoundError(PineconeAssistantError):
    """Raised when a requested resource is not found (404 Not Found)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, error_code="NOT_FOUND")


class RateLimitError(PineconeAssistantError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, error_code="RATE_LIMIT")


class ValidationError(PineconeAssistantError):
    """Raised when input validation fails (400 Bad Request)."""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, error_code="VALIDATION_ERROR")


class ConfigurationError(PineconeAssistantError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Invalid configuration"):
        super().__init__(message, error_code="CONFIG_ERROR")


class TimeoutError(PineconeAssistantError):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message, error_code="TIMEOUT")


class ServerError(PineconeAssistantError):
    """Raised when the API server returns an error (500 Internal Server Error)."""

    def __init__(self, message: str = "Server error"):
        super().__init__(message, error_code="SERVER_ERROR")


class CircuitBreakerError(PineconeAssistantError):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, error_code="CIRCUIT_BREAKER_OPEN")


class SerializationError(PineconeAssistantError):
    """Raised when object serialization fails."""

    def __init__(self, message: str = "Serialization failed"):
        super().__init__(message, error_code="SERIALIZATION_ERROR")


# Additional HTTP error types for comprehensive coverage

class ConflictError(PineconeAssistantError):
    """Raised when resource conflict occurs (409 Conflict)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, error_code="CONFLICT")


class PayloadTooLargeError(PineconeAssistantError):
    """Raised when request payload is too large (413 Payload Too Large)."""

    def __init__(self, message: str = "Request payload too large"):
        super().__init__(message, error_code="PAYLOAD_TOO_LARGE")


class BadGatewayError(PineconeAssistantError):
    """Raised when upstream service returns error (502 Bad Gateway)."""

    def __init__(self, message: str = "Bad gateway"):
        super().__init__(message, error_code="BAD_GATEWAY")


class ServiceUnavailableError(PineconeAssistantError):
    """Raised when service is temporarily unavailable (503 Service Unavailable)."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, error_code="SERVICE_UNAVAILABLE")


class GatewayTimeoutError(PineconeAssistantError):
    """Raised when gateway times out (504 Gateway Timeout)."""

    def __init__(self, message: str = "Gateway timeout"):
        super().__init__(message, error_code="GATEWAY_TIMEOUT")
