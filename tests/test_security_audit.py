"""Tests for security audit logger (L-4 remediation)."""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.util.security_audit import SecurityAuditLogger


class TestSecurityAuditLogger:
    """Test structured security event logging."""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        """Create a SecurityAuditLogger with temp log file."""
        log_file = str(tmp_path / "test_security_audit.log")
        return SecurityAuditLogger(log_file_path=log_file)

    @pytest.fixture
    def log_capture(self):
        """Capture log output for assertions."""
        handler = logging.handlers.MemoryHandler(capacity=100)

        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

        capture = CaptureHandler()
        audit_logger = logging.getLogger("security_audit")
        audit_logger.addHandler(capture)
        yield capture
        audit_logger.removeHandler(capture)

    def test_log_event_returns_structured_json(self, audit_logger):
        """Verify log_event returns structured dict with required fields."""
        event = audit_logger.log_event(
            event_type="test_event",
            details={"key": "value"},
            request_id="abc123",
            severity="warning",
        )

        assert event["event_type"] == "test_event"
        assert event["request_id"] == "abc123"
        assert event["severity"] == "warning"
        assert event["details"] == {"key": "value"}
        assert "timestamp" in event

    def test_log_event_timestamp_is_utc_iso(self, audit_logger):
        """Verify timestamp is in UTC ISO format."""
        event = audit_logger.log_event("test", request_id="req1")
        timestamp = event["timestamp"]
        # Should end with +00:00 (UTC)
        assert "+00:00" in timestamp or "Z" in timestamp

    def test_log_auth_failure(self, audit_logger):
        """Test auth failure event structure."""
        event = audit_logger.log_auth_failure(
            assistant_name="test-assistant",
            failure_reason="invalid_api_key",
            request_id="req123",
        )

        assert event["event_type"] == "auth_failure"
        assert event["severity"] == "error"
        assert event["details"]["assistant"] == "test-assistant"
        assert event["details"]["failure_reason"] == "invalid_api_key"

    def test_log_authorization_failure(self, audit_logger):
        """Test authorization failure event."""
        event = audit_logger.log_authorization_failure(
            assistant_name="test-assistant",
            request_id="req123",
        )

        assert event["event_type"] == "authorization_failure"
        assert event["severity"] == "error"
        assert event["details"]["assistant"] == "test-assistant"

    def test_log_rate_limit(self, audit_logger):
        """Test rate limit event."""
        event = audit_logger.log_rate_limit(
            tool_name="assistant_chat",
            request_id="req123",
        )

        assert event["event_type"] == "rate_limit"
        assert event["severity"] == "warning"
        assert event["details"]["tool"] == "assistant_chat"

    def test_log_validation_failure(self, audit_logger):
        """Test validation failure event."""
        event = audit_logger.log_validation_failure(
            tool_name="assistant_chat",
            error_message="Missing required field",
            request_id="req123",
        )

        assert event["event_type"] == "validation_failure"
        assert event["details"]["error"] == "Missing required field"

    def test_log_config_change(self, audit_logger):
        """Test configuration change event."""
        changes = {
            "assistant_name": {"old": "old-name", "new": "new-name"},
            "model": {"old": "gpt-4o", "new": "claude-3-7-sonnet"},
        }
        event = audit_logger.log_config_change(
            changes=changes,
            request_id="req123",
        )

        assert event["event_type"] == "config_change"
        assert event["details"]["changes"] == changes

    def test_log_circuit_breaker_state(self, audit_logger):
        """Test circuit breaker state change event."""
        event = audit_logger.log_circuit_breaker_state(
            breaker_name="api_breaker",
            old_state="closed",
            new_state="open",
            failure_count=5,
        )

        assert event["event_type"] == "circuit_breaker_open"
        assert event["severity"] == "error"
        assert event["details"]["breaker_name"] == "api_breaker"
        assert event["details"]["failure_count"] == 5

    def test_circuit_breaker_recovery_event_type(self, audit_logger):
        """Test circuit breaker recovery uses different event type."""
        event = audit_logger.log_circuit_breaker_state(
            breaker_name="api_breaker",
            old_state="half_open",
            new_state="closed",
            failure_count=0,
        )

        assert event["event_type"] == "circuit_breaker_state"
        assert event["severity"] == "warning"

    def test_log_event_auto_detects_request_id(self, audit_logger):
        """Test that request_id is auto-generated when not provided."""
        event = audit_logger.log_event("test")
        assert event["request_id"]  # Should not be empty
        assert len(event["request_id"]) > 0

    def test_event_json_is_valid(self, audit_logger):
        """Verify the logged event is valid JSON."""
        event = audit_logger.log_event(
            event_type="test",
            details={"nested": {"data": [1, 2, 3]}},
            request_id="req1",
        )

        # Should be serializable to JSON
        json_str = json.dumps(event)
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "test"

    def test_sensitive_data_not_in_event(self, audit_logger):
        """Verify API keys are not stored in audit events."""
        event = audit_logger.log_auth_failure(
            assistant_name="test-assistant",
            failure_reason="invalid_api_key",
            request_id="req123",
        )

        event_str = json.dumps(event)
        assert "pcsk_" not in event_str
        assert "password" not in event_str.lower()

    def test_log_file_created(self, tmp_path):
        """Test that the security audit log file is created."""
        log_file = str(tmp_path / "audit.log")
        audit = SecurityAuditLogger(log_file_path=log_file)
        audit.log_event("test", request_id="req1")

        assert Path(log_file).exists()

    def test_forwards_to_monitor(self, audit_logger):
        """Test that events are forwarded to the monitoring system."""
        with patch("src.util.security_audit.monitor") as mock_monitor:
            audit_logger.log_event("auth_failure", request_id="req1")
            mock_monitor.record_event.assert_called_once_with("auth_failure")
