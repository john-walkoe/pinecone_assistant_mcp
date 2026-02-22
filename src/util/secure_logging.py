"""
Secure logging utilities for Pinecone Assistant MCP.

This module provides utilities for sanitizing log messages to prevent
accidental exposure of sensitive information like API keys and tokens.
"""

import logging
import re
from typing import Tuple

# Sensitive patterns to redact from logs
SENSITIVE_PATTERNS = [
    r'pcsk_[A-Za-z0-9_-]+',  # Pinecone API keys
    r'Bearer\s+[A-Za-z0-9._-]+',  # Bearer tokens
    r'Authorization:\s*[Bb]earer\s+[A-Za-z0-9._-]+',  # Authorization headers
    r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+',  # API key patterns
    r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+',  # Password patterns
    r'token["\']?\s*[:=]\s*["\']?[^"\'\s]+',  # Token patterns
]

logger = logging.getLogger(__name__)


def sanitize_message(message: str, max_length: int = 5000) -> str:
    """
    Remove sensitive information from a message and prevent log injection.

    Args:
        message: The message to sanitize
        max_length: Maximum length for log message (default: 5000 chars)

    Returns:
        Sanitized message with sensitive data replaced with [REDACTED]
        and control characters escaped to prevent log injection
    """
    sanitized = message

    # SECURITY FIX (L-7): Prevent log injection by escaping newlines and control chars
    sanitized = sanitized.replace('\n', '\\n')
    sanitized = sanitized.replace('\r', '\\r')
    sanitized = sanitized.replace('\t', '\\t')

    # Redact sensitive patterns (API keys, passwords, tokens)
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

    # SECURITY FIX (L-7): Truncate excessively long messages
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... (truncated)"

    return sanitized


def classify_api_error(error: Exception) -> Tuple[str, str]:
    """
    Classify an API error without exposing sensitive details.

    Args:
        error: The exception to classify

    Returns:
        Tuple of (error_category, user_message)
    """
    error_str = str(error).lower()

    # Check for specific error patterns
    if "400" in error_str or "bad request" in error_str or "invalid" in error_str:
        return "validation", "Invalid request format"

    if "401" in error_str or "unauthorized" in error_str:
        return "authentication", "Authentication failed"

    if "403" in error_str or "forbidden" in error_str:
        return "authorization", "Access forbidden"

    if "404" in error_str or "not found" in error_str:
        return "not_found", "Resource not found"

    if "429" in error_str or "rate limit" in error_str:
        return "rate_limit", "Rate limit exceeded"

    if "500" in error_str or "internal server" in error_str:
        return "server_error", "Server error"

    if "timeout" in error_str or "timed out" in error_str:
        return "timeout", "Request timeout"

    return "api_error", "Request failed"


def get_error_help(error_category: str) -> str:
    """
    Get helpful guidance for a specific error category.

    Args:
        error_category: The error category from classify_api_error

    Returns:
        User-friendly help message
    """
    help_map = {
        "authentication": "Check your PINECONE_ASSISTANT_API_KEY environment variable",
        "authorization": "Verify your API key has access to the specified assistant",
        "not_found": "Verify PINECONE_ASSISTANT_NAME is correct",
        "rate_limit": "Wait a moment before making more requests",
        "validation": "Check your input parameters",
        "timeout": "The request took too long - try again or reduce request size",
        "server_error": "The API service is experiencing issues - try again later",
    }
    return help_map.get(error_category, "Contact support if this issue persists")


def log_error_safely(
    logger_instance: logging.Logger,
    context: str,
    error: Exception,
    include_traceback: bool = False
) -> None:
    """
    Log an error with sensitive information redacted.

    Args:
        logger_instance: The logger to use
        context: Context string describing where the error occurred
        error: The exception to log
        include_traceback: Whether to include full traceback (for debug mode)
    """
    # Classify the error for safe logging
    error_category, _ = classify_api_error(error)

    # Sanitize the error message
    sanitized_error = sanitize_message(str(error))

    # Log the error
    log_message = f"{context} failed: {error_category}"
    logger_instance.error(log_message, exc_info=include_traceback)

    # In debug mode, log sanitized details
    if include_traceback:
        logger_instance.debug(f"Sanitized error details: {sanitized_error}")


class SecureFormatter(logging.Formatter):
    """
    Custom log formatter that automatically redacts sensitive information.

    This formatter wraps the standard logging formatter and sanitizes
    all log messages before they are written.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with sensitive information redacted.

        Args:
            record: The log record to format

        Returns:
            Formatted and sanitized log message
        """
        # Format the message normally
        message = super().format(record)

        # Sanitize sensitive information
        return sanitize_message(message)


def setup_secure_logging(
    logger_name: str = None,
    level: int = logging.INFO,
    include_traceback: bool = False,
    log_format: str = None,
    enable_file_logging: bool = False,
    log_file_path: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # SECURITY FIX (L-3): 10MB default
    backup_count: int = 5  # SECURITY FIX (L-3): Keep 5 old log files
) -> logging.Logger:
    """
    Set up a logger with secure formatting and log rotation.

    Args:
        logger_name: Name of the logger (None for root logger)
        level: Logging level
        include_traceback: Whether to include tracebacks in error logs
        log_format: Log message format string (default: standard format)
        enable_file_logging: Whether to enable file logging (default: False)
        log_file_path: Path to log file (default: logs/pinecone_assistant.log)
        max_bytes: Maximum log file size before rotation (default: 10MB)
        backup_count: Number of rotated log files to keep (default: 5)

    Returns:
        Configured logger instance with SecureFormatter and log rotation
    """
    from logging.handlers import RotatingFileHandler  # SECURITY FIX (L-3)
    import os

    logger_instance = logging.getLogger(logger_name)
    logger_instance.setLevel(level)

    # Remove existing handlers
    logger_instance.handlers = []

    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Use secure formatter
    formatter = SecureFormatter(log_format)

    # Create console handler with secure formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger_instance.addHandler(console_handler)

    # SECURITY FIX (L-3): Optional file handler with rotation
    if enable_file_logging:
        if log_file_path is None:
            log_file_path = 'logs/pinecone_assistant.log'

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # Use RotatingFileHandler for automatic log rotation
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger_instance.addHandler(file_handler)

    return logger_instance


# Aliases for backward compatibility with tests
SecureLogger = SecureFormatter
sanitize_for_logging = sanitize_message
