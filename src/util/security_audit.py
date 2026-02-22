"""
Dedicated security audit logger for Pinecone Assistant MCP.

Produces structured JSON security events to a separate audit log file,
enabling breach detection, forensic analysis, and compliance monitoring.

Security Fix: L-4 (CWE-778 - Insufficient Logging, CWE-223 - Omission of Security-relevant Information)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    from .secure_logging import setup_secure_logging
    from .error_context import get_request_id
    from .monitoring import monitor
except ImportError:
    from secure_logging import setup_secure_logging
    from error_context import get_request_id
    from monitoring import monitor


class SecurityAuditLogger:
    """
    Dedicated logger for security-relevant events.

    Writes structured JSON events to a separate security audit log file
    and forwards events to the monitoring system for threshold alerting.
    """

    def __init__(self, log_file_path: Optional[str] = None):
        """
        Initialize the security audit logger.

        Args:
            log_file_path: Path to security audit log file.
                          Defaults to ~/.pinecone_assistant/logs/security_audit.log
        """
        from pathlib import Path

        if log_file_path is None:
            log_file_path = str(
                Path.home() / ".pinecone_assistant" / "logs" / "security_audit.log"
            )

        self._audit_logger = setup_secure_logging(
            logger_name="security_audit",
            level=logging.WARNING,
            enable_file_logging=True,
            log_file_path=log_file_path,
            max_bytes=10 * 1024 * 1024,  # 10MB
            backup_count=10,  # Keep more for compliance
        )
        # Prevent propagation to root logger to avoid duplicate output
        self._audit_logger.propagate = False

    def log_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        severity: str = "warning",
    ) -> dict:
        """
        Log a structured security event.

        Args:
            event_type: Type of security event (e.g., "auth_failure", "rate_limit")
            details: Additional event details
            request_id: Correlation ID (auto-detected if not provided)
            severity: Log severity ("warning", "error", "critical")

        Returns:
            The structured event dict that was logged.
        """
        if request_id is None:
            request_id = get_request_id()

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "request_id": request_id,
            "severity": severity,
            "details": details or {},
        }

        event_json = json.dumps(event)

        # Log to dedicated audit file at appropriate level
        log_method = {
            "warning": self._audit_logger.warning,
            "error": self._audit_logger.error,
            "critical": self._audit_logger.critical,
        }.get(severity, self._audit_logger.warning)

        log_method(event_json)

        # Forward to monitoring system for threshold alerting
        monitor.record_event(event_type)

        return event

    def log_auth_failure(
        self,
        assistant_name: str,
        failure_reason: str = "invalid_api_key",
        request_id: Optional[str] = None,
    ) -> dict:
        """Log an authentication failure event."""
        return self.log_event(
            event_type="auth_failure",
            details={
                "assistant": assistant_name,
                "failure_reason": failure_reason,
            },
            request_id=request_id,
            severity="error",
        )

    def log_authorization_failure(
        self,
        assistant_name: str,
        request_id: Optional[str] = None,
    ) -> dict:
        """Log an authorization failure event."""
        return self.log_event(
            event_type="authorization_failure",
            details={"assistant": assistant_name},
            request_id=request_id,
            severity="error",
        )

    def log_rate_limit(
        self,
        tool_name: str,
        request_id: Optional[str] = None,
    ) -> dict:
        """Log a rate limit event."""
        return self.log_event(
            event_type="rate_limit",
            details={"tool": tool_name},
            request_id=request_id,
            severity="warning",
        )

    def log_validation_failure(
        self,
        tool_name: str,
        error_message: str,
        request_id: Optional[str] = None,
    ) -> dict:
        """Log a validation failure event."""
        return self.log_event(
            event_type="validation_failure",
            details={"tool": tool_name, "error": error_message},
            request_id=request_id,
            severity="warning",
        )

    def log_config_change(
        self,
        changes: Dict[str, Dict[str, str]],
        request_id: Optional[str] = None,
    ) -> dict:
        """
        Log a configuration change event.

        Args:
            changes: Dictionary of {field: {"old": old_value, "new": new_value}}
            request_id: Correlation ID
        """
        return self.log_event(
            event_type="config_change",
            details={"changes": changes},
            request_id=request_id,
            severity="warning",
        )

    def log_circuit_breaker_state(
        self,
        breaker_name: str,
        old_state: str,
        new_state: str,
        failure_count: int = 0,
    ) -> dict:
        """Log a circuit breaker state transition."""
        # Map to monitoring event type
        event_type = (
            "circuit_breaker_open" if new_state == "open"
            else "circuit_breaker_state"
        )
        return self.log_event(
            event_type=event_type,
            details={
                "breaker_name": breaker_name,
                "old_state": old_state,
                "new_state": new_state,
                "failure_count": failure_count,
            },
            severity="error" if new_state == "open" else "warning",
        )


# Singleton instance
security_audit = SecurityAuditLogger()
