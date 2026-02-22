"""
Utility modules for exceptions and secure logging.

Cross-cutting concerns for error handling, logging, and security. Provides
custom exception hierarchy and secure logging utilities that automatically
sanitize sensitive information.

Exceptions:
    - Custom exception hierarchy with error codes
    - Categorized exceptions for specific error types
    - All exceptions inherit from PineconeAssistantError

Secure Logging:
    - Automatic API key and token redaction
    - Error classification without exposing internals
    - Context-aware help messages for users
    - SecureFormatter for automatic log sanitization

Security Features:
    - Pattern-based sensitive data detection
    - Configurable redaction strategies
    - Debug mode awareness for development
    - Production-safe error messages
"""

from .exceptions import (
    PineconeAssistantError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitError,
    ValidationError,
    ConfigurationError,
    TimeoutError,
    ServerError,
    CircuitBreakerError,
    SerializationError,
)
from .secure_logging import (
    SecureFormatter,
    sanitize_message,
    classify_api_error,
    log_error_safely,
    get_error_help,
    setup_secure_logging,
    SecureLogger,
    sanitize_for_logging,
)
from .security_audit import SecurityAuditLogger, security_audit
from .monitoring import SimpleMonitor, monitor

__all__ = [
    "PineconeAssistantError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "RateLimitError",
    "ValidationError",
    "ConfigurationError",
    "TimeoutError",
    "ServerError",
    "CircuitBreakerError",
    "SerializationError",
    "SecureFormatter",
    "sanitize_message",
    "classify_api_error",
    "log_error_safely",
    "get_error_help",
    "setup_secure_logging",
    "SecureLogger",
    "sanitize_for_logging",
    "SecurityAuditLogger",
    "security_audit",
    "SimpleMonitor",
    "monitor",
]
