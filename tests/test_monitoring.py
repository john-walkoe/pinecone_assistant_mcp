"""Tests for monitoring and threshold alerting (L-6 remediation)."""

import json
import time
import threading
from pathlib import Path

import pytest

from src.util.monitoring import SimpleMonitor, AlertThreshold, DEFAULT_THRESHOLDS


class TestSimpleMonitor:
    """Test lightweight monitoring and alerting."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a fresh monitor with temp alert file."""
        alerts_file = tmp_path / "alerts.jsonl"
        return SimpleMonitor(alerts_file=alerts_file)

    @pytest.fixture
    def low_threshold_monitor(self, tmp_path):
        """Monitor with low thresholds for easy testing."""
        alerts_file = tmp_path / "alerts.jsonl"
        thresholds = {
            "test_event": AlertThreshold(
                metric_name="test_event",
                threshold=3,
                window_seconds=60,
                severity="warning",
            ),
        }
        return SimpleMonitor(thresholds=thresholds, alerts_file=alerts_file)

    def test_record_event_no_threshold(self, monitor):
        """Recording an event without a threshold returns None."""
        result = monitor.record_event("unknown_event")
        assert result is None

    def test_record_event_below_threshold(self, monitor):
        """Events below threshold do not trigger alerts."""
        result = monitor.record_event("auth_failure")
        assert result is None

    def test_threshold_breach_triggers_alert(self, low_threshold_monitor):
        """Reaching threshold triggers an alert."""
        mon = low_threshold_monitor
        # Record events up to threshold
        mon.record_event("test_event")
        mon.record_event("test_event")
        alert = mon.record_event("test_event")

        assert alert is not None
        assert alert["alert_type"] == "threshold_breach"
        assert alert["severity"] == "warning"
        assert alert["metric_name"] == "test_event"
        assert alert["event_count"] >= 3

    def test_alert_contains_required_fields(self, low_threshold_monitor):
        """Alert dict contains all required fields."""
        mon = low_threshold_monitor
        for _ in range(3):
            mon.record_event("test_event")

        alert = mon.record_event("test_event")
        assert alert is not None
        assert "timestamp" in alert
        assert "alert_type" in alert
        assert "severity" in alert
        assert "metric_name" in alert
        assert "event_count" in alert
        assert "threshold" in alert
        assert "window_seconds" in alert
        assert "message" in alert

    def test_alert_written_to_jsonl_file(self, low_threshold_monitor, tmp_path):
        """Alert is appended to JSONL file."""
        mon = low_threshold_monitor
        for _ in range(3):
            mon.record_event("test_event")

        alerts_file = mon._alerts_file
        assert alerts_file.exists()

        lines = alerts_file.read_text().strip().split("\n")
        assert len(lines) >= 1

        # Each line should be valid JSON
        parsed = json.loads(lines[0])
        assert parsed["alert_type"] == "threshold_breach"

    def test_old_events_expire(self, tmp_path):
        """Events outside the window are removed."""
        alerts_file = tmp_path / "alerts.jsonl"
        thresholds = {
            "test_event": AlertThreshold(
                metric_name="test_event",
                threshold=3,
                window_seconds=1,  # 1 second window
                severity="warning",
            ),
        }
        mon = SimpleMonitor(thresholds=thresholds, alerts_file=alerts_file)

        # Record 2 events
        mon.record_event("test_event")
        mon.record_event("test_event")

        # Wait for events to expire
        time.sleep(1.1)

        # This should not trigger (old events expired)
        result = mon.record_event("test_event")
        assert result is None

    def test_get_metrics_returns_counts(self, monitor):
        """get_metrics returns event counts."""
        monitor.record_event("auth_failure")
        monitor.record_event("auth_failure")
        monitor.record_event("rate_limit")

        metrics = monitor.get_metrics()
        assert metrics["event_counts"]["auth_failure"] == 2
        assert metrics["event_counts"]["rate_limit"] == 1

    def test_get_metrics_threshold_status(self, low_threshold_monitor):
        """get_metrics shows threshold percentage."""
        mon = low_threshold_monitor
        mon.record_event("test_event")

        metrics = mon.get_metrics()
        status = metrics["threshold_status"]["test_event"]
        assert status["active_events"] == 1
        assert status["threshold"] == 3
        assert status["percentage"] == pytest.approx(33.3, abs=0.1)

    def test_get_metrics_alert_count(self, low_threshold_monitor):
        """get_metrics tracks total alert count."""
        mon = low_threshold_monitor
        for _ in range(3):
            mon.record_event("test_event")

        metrics = mon.get_metrics()
        assert metrics["total_alerts"] >= 1

    def test_reset_clears_events(self, monitor):
        """reset() clears all tracked events."""
        monitor.record_event("auth_failure")
        monitor.record_event("rate_limit")
        monitor.reset()

        metrics = monitor.get_metrics()
        assert metrics["event_counts"] == {}
        assert metrics["total_alerts"] == 0

    def test_thread_safety(self, tmp_path):
        """Monitor is thread-safe under concurrent access."""
        alerts_file = tmp_path / "alerts.jsonl"
        thresholds = {
            "concurrent_event": AlertThreshold(
                metric_name="concurrent_event",
                threshold=50,
                window_seconds=60,
                severity="warning",
            ),
        }
        mon = SimpleMonitor(thresholds=thresholds, alerts_file=alerts_file)

        errors = []

        def record_events():
            try:
                for _ in range(20):
                    mon.record_event("concurrent_event")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        metrics = mon.get_metrics()
        assert metrics["event_counts"]["concurrent_event"] == 100

    def test_default_thresholds_loaded(self):
        """Default thresholds include auth_failure and rate_limit."""
        assert "auth_failure" in DEFAULT_THRESHOLDS
        assert "rate_limit" in DEFAULT_THRESHOLDS
        assert "circuit_breaker_open" in DEFAULT_THRESHOLDS

    def test_max_events_bounded(self, tmp_path):
        """Events per type are bounded to prevent unbounded memory."""
        alerts_file = tmp_path / "alerts.jsonl"
        mon = SimpleMonitor(
            thresholds={},
            alerts_file=alerts_file,
            max_events_per_type=10,
        )

        for _ in range(50):
            mon.record_event("bounded_event")

        metrics = mon.get_metrics()
        assert metrics["event_counts"]["bounded_event"] == 10

    def test_alert_file_directory_created(self, tmp_path):
        """Alert file parent directory is created if it doesn't exist."""
        nested_file = tmp_path / "nested" / "dir" / "alerts.jsonl"
        thresholds = {
            "test": AlertThreshold("test", 1, 60, "warning"),
        }
        mon = SimpleMonitor(thresholds=thresholds, alerts_file=nested_file)
        mon.record_event("test")

        assert nested_file.exists()
