"""
Circuit breaker pattern implementation for Pinecone Assistant MCP.

This module implements the circuit breaker pattern to prevent cascading failures
and provide fast failure when a service is unavailable.
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Callable, TypeVar, Optional

try:
    from ..util.exceptions import CircuitBreakerError
    from ..util.secure_logging import setup_secure_logging
    from ..util.security_audit import security_audit
except ImportError:
    from util.exceptions import CircuitBreakerError
    from util.secure_logging import setup_secure_logging
    from util.security_audit import security_audit

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"      # Failures detected, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered

    State transitions:
    - CLOSED -> OPEN: When failure threshold is exceeded
    - OPEN -> HALF_OPEN: After recovery timeout
    - HALF_OPEN -> CLOSED: When test request succeeds
    - HALF_OPEN -> OPEN: When test request fails
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name for logging/identification
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.recovery_timeout

    def _record_success(self):
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            # Success in half-open state means service recovered
            old_state = self.state.value
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker '{self.name}' closed (service recovered)")
            # SECURITY FIX (L-4): Audit circuit breaker recovery
            security_audit.log_circuit_breaker_state(
                self.name, old_state, self.state.value, self.failure_count
            )
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self.failure_count = 0

    def _record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open means service still down
            old_state = self.state.value
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' re-opened (service still down)")
            # SECURITY FIX (L-4): Audit circuit breaker state change
            security_audit.log_circuit_breaker_state(
                self.name, old_state, self.state.value, self.failure_count
            )
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                old_state = self.state.value
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
                )
                # SECURITY FIX (L-4): Audit circuit breaker opening
                security_audit.log_circuit_breaker_state(
                    self.name, old_state, self.state.value, self.failure_count
                )

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Any exception raised by the function
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            logger.info(f"Circuit breaker '{self.name}' half-open (testing recovery)")

        # Reject request if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable (failed {self.failure_count} times). "
                f"Will retry after {self.recovery_timeout}s."
            )

        # Attempt the operation
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise
        except Exception as e:
            # Unexpected exceptions don't affect circuit state
            logger.debug(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Any exception raised by the function
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            logger.info(f"Circuit breaker '{self.name}' half-open (testing recovery)")

        # Reject request if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable (failed {self.failure_count} times). "
                f"Will retry after {self.recovery_timeout}s."
            )

        # Attempt the operation
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise
        except Exception as e:
            # Unexpected exceptions don't affect circuit state
            logger.debug(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise

    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_status(self) -> dict:
        """
        Get current circuit breaker status.

        Returns:
            Dictionary with current state information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
        }


def circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception
):
    """
    Decorator to wrap a function with circuit breaker protection.

    Args:
        name: Circuit breaker name for logging
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers circuit

    Returns:
        Decorated function with circuit breaker
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await breaker.call_async(func, *args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Use this to coordinate circuit breakers across your application.
    """

    def __init__(self):
        """Initialize the registry."""
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create a new one.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit

        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
        return self._breakers[name]

    def get_status_all(self) -> dict[str, dict]:
        """
        Get status of all circuit breakers.

        Returns:
            Dictionary mapping names to status dictionaries
        """
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Alias for backward compatibility with tests
CircuitBreakerOpen = CircuitBreakerError
