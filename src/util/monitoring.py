"""
Lightweight monitoring and threshold-based alerting for Pinecone Assistant MCP.

Tracks security-relevant events and triggers alerts when configurable
thresholds are breached. Outputs alerts to JSONL file for external
monitoring/SIEM integration.

Security Fix: L-6 (CWE-223 - Omission of Security-relevant Information)
"""

import json
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Deque, Optional


@dataclass(frozen=True)
class AlertThreshold:
    """Configuration for an event threshold that triggers an alert."""
    metric_name: str
    threshold: int
    window_seconds: int
    severity: str  # "warning" or "critical"


# Default thresholds for security events
DEFAULT_THRESHOLDS: Dict[str, AlertThreshold] = {
    "auth_failure": AlertThreshold(
        metric_name="auth_failure",
        threshold=5,
        window_seconds=300,
        severity="warning"
    ),
    "rate_limit": AlertThreshold(
        metric_name="rate_limit",
        threshold=10,
        window_seconds=60,
        severity="critical"
    ),
    "circuit_breaker_open": AlertThreshold(
        metric_name="circuit_breaker_open",
        threshold=3,
        window_seconds=600,
        severity="critical"
    ),
}


class SimpleMonitor:
    """
    Lightweight in-process monitor for security-relevant events.

    Records timestamped events, checks configurable thresholds,
    and writes alerts to a JSONL file for external monitoring.

    Thread-safe for concurrent access.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, AlertThreshold]] = None,
        alerts_file: Optional[Path] = None,
        max_events_per_type: int = 1000
    ):
        """
        Initialize the monitor.

        Args:
            thresholds: Event thresholds that trigger alerts.
                       Defaults to DEFAULT_THRESHOLDS.
            alerts_file: Path to JSONL alert output file.
                        Defaults to ~/.pinecone_assistant/logs/alerts.jsonl
            max_events_per_type: Maximum events stored per type (prevents unbounded memory).
        """
        self.thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        self._max_events = max_events_per_type
        self._alert_count = 0

        if alerts_file is None:
            self._alerts_file = Path.home() / ".pinecone_assistant" / "logs" / "alerts.jsonl"
        else:
            self._alerts_file = alerts_file

    def record_event(self, event_type: str) -> Optional[dict]:
        """
        Record a security event and check thresholds.

        Args:
            event_type: Type of event (e.g., "auth_failure", "rate_limit")

        Returns:
            Alert dict if threshold was breached, None otherwise.
        """
        with self._lock:
            if event_type not in self._events:
                self._events[event_type] = deque(maxlen=self._max_events)

            now = time.time()
            self._events[event_type].append(now)

            if event_type in self.thresholds:
                return self._check_threshold(event_type, now)
            return None

    def _check_threshold(self, event_type: str, now: float) -> Optional[dict]:
        """Check if an event type has breached its threshold. Must hold lock."""
        threshold = self.thresholds[event_type]
        events = self._events[event_type]

        # Remove events outside the window
        cutoff = now - threshold.window_seconds
        while events and events[0] < cutoff:
            events.popleft()

        # Check if threshold breached
        if len(events) >= threshold.threshold:
            alert = self._build_alert(threshold, len(events))
            self._write_alert(alert)
            return alert
        return None

    def _build_alert(self, threshold: AlertThreshold, count: int) -> dict:
        """Build a structured alert dictionary."""
        self._alert_count += 1
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_type": "threshold_breach",
            "severity": threshold.severity,
            "metric_name": threshold.metric_name,
            "event_count": count,
            "threshold": threshold.threshold,
            "window_seconds": threshold.window_seconds,
            "message": (
                f"SECURITY ALERT: {threshold.metric_name} threshold breached "
                f"({count} events in {threshold.window_seconds}s, "
                f"threshold: {threshold.threshold})"
            ),
        }

    def _write_alert(self, alert: dict) -> None:
        """Append alert to JSONL file for external monitoring."""
        try:
            self._alerts_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._alerts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert) + "\n")
        except OSError:
            # Don't let alert file failures crash the application
            pass

    def get_metrics(self) -> dict:
        """
        Get current monitoring metrics.

        Returns:
            Dictionary with event counts and alert status.
        """
        with self._lock:
            now = time.time()
            metrics = {
                "total_alerts": self._alert_count,
                "event_counts": {},
                "threshold_status": {},
            }

            for event_type, events in self._events.items():
                # Count events within their threshold window
                if event_type in self.thresholds:
                    window = self.thresholds[event_type].window_seconds
                    cutoff = now - window
                    active_count = sum(1 for t in events if t >= cutoff)
                    threshold_val = self.thresholds[event_type].threshold
                    metrics["threshold_status"][event_type] = {
                        "active_events": active_count,
                        "threshold": threshold_val,
                        "percentage": round((active_count / threshold_val) * 100, 1)
                        if threshold_val > 0 else 0,
                    }
                metrics["event_counts"][event_type] = len(events)

            return metrics

    def reset(self) -> None:
        """Reset all event tracking. Useful for testing."""
        with self._lock:
            self._events.clear()
            self._alert_count = 0


# Global monitor instance
monitor = SimpleMonitor()
