"""Client-side rate limiting with sliding window algorithm."""

import time
import threading
from collections import deque
from typing import Optional, Tuple


class RateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        name: str = "default"
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            name: Identifier for this limiter
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
        self._requests: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check_rate(self, client_id: str = "default") -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.

        Args:
            client_id: Identifier for the client (default: "default")

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: Optional[int])
        """
        with self._lock:
            now = time.time()

            # Initialize deque for this client
            if client_id not in self._requests:
                self._requests[client_id] = deque(maxlen=self.max_requests * 2)

            requests = self._requests[client_id]
            cutoff = now - self.window_seconds

            # Remove expired requests
            while requests and requests[0] < cutoff:
                requests.popleft()

            # Check if limit exceeded
            if len(requests) >= self.max_requests:
                retry_after = int(requests[0] + self.window_seconds - now) + 1
                return False, retry_after

            # Record this request
            requests.append(now)
            return True, None

    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        with self._lock:
            return {
                "name": self.name,
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "active_clients": len(self._requests),
                "current_usage": {
                    client_id: len(requests)
                    for client_id, requests in self._requests.items()
                }
            }
