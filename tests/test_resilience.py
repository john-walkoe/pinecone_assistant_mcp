"""Tests for resilience components (retry, circuit breaker, cache, etc.)."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from src.resilience.retry_utils import RetryableHTTPClient, exponential_backoff
from src.resilience.circuit_breaker import CircuitBreaker
from src.util.exceptions import CircuitBreakerError as CircuitBreakerOpen
from src.resilience.cache import ResponseCache
from src.resilience.bulkhead import BulkheadIsolator
from src.resilience.fallback import FallbackChain, FallbackStrategy


class TestRetryUtils:
    """Test retry utilities and exponential backoff."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        # Test basic exponential growth
        delay1 = exponential_backoff(attempt=1, base_delay=1.0, max_delay=60.0, backoff_factor=2.0)
        delay2 = exponential_backoff(attempt=2, base_delay=1.0, max_delay=60.0, backoff_factor=2.0)
        delay3 = exponential_backoff(attempt=3, base_delay=1.0, max_delay=60.0, backoff_factor=2.0)

        # Should grow exponentially (with jitter, so test ranges)
        assert 0.5 <= delay1 <= 3.0  # ~1s * 2^1 with jitter
        assert 1.0 <= delay2 <= 6.0  # ~1s * 2^2 with jitter
        assert 2.0 <= delay3 <= 12.0  # ~1s * 2^3 with jitter

        # Test max delay cap
        delay_high = exponential_backoff(attempt=10, base_delay=1.0, max_delay=5.0, backoff_factor=2.0)
        assert delay_high <= 5.0

    def test_retryable_http_client_success(self):
        """Test successful execution without retries."""
        mock_func = Mock(return_value="success")

        executor = RetryableHTTPClient(max_retries=3, base_delay=0.1)
        result = executor.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retryable_http_client_retry_on_failure(self):
        """Test retry executor retries on failure."""
        # First two calls fail, third succeeds
        mock_func = Mock(side_effect=[
            ConnectionError("Connection timeout"),
            ConnectionError("Server error"),
            "success"
        ])

        executor = RetryableHTTPClient(max_retries=3, base_delay=0.01)  # Fast retry for testing
        result = executor.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retryable_http_client_max_retries_exceeded(self):
        """Test retry executor when max retries exceeded."""
        mock_func = Mock(side_effect=ConnectionError("Persistent failure"))

        executor = RetryableHTTPClient(max_retries=2, base_delay=0.01)

        with pytest.raises(ConnectionError, match="Persistent failure"):
            executor.execute(mock_func)

        assert mock_func.call_count == 3  # Initial + 2 retries


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state (normal operation)."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        # Should be able to execute initially
        mock_func = Mock(return_value="success")
        result = cb.call(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Cause failures to reach threshold
        mock_func = Mock(side_effect=Exception("Test failure"))

        # First failure
        with pytest.raises(Exception):
            cb.call(mock_func)

        # Second failure should open circuit
        with pytest.raises(Exception):
            cb.call(mock_func)

        # Third call should be blocked by open circuit
        with pytest.raises(CircuitBreakerOpen):
            cb.call(mock_func)

        # Should only be called twice (circuit opened after 2nd)
        assert mock_func.call_count == 2

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state for recovery."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)  # Very short timeout

        # Open the circuit
        mock_func = Mock(side_effect=Exception("Test failure"))
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(mock_func)

        # Wait for recovery timeout
        time.sleep(0.02)

        # Should allow one call to test recovery
        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = cb.call(mock_func)
        assert result == "success"

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery from half-open to closed."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)

        # Open circuit
        mock_func = Mock(side_effect=Exception("Test failure"))
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(mock_func)

        # Wait for half-open
        time.sleep(0.02)

        # Successful operation should close circuit
        mock_func.side_effect = None
        mock_func.return_value = "success"
        cb.call(mock_func)

        # Should now accept calls normally
        cb.call(mock_func)
        assert mock_func.call_count == 4  # 2 failures + 2 successes

    def test_circuit_breaker_decorator(self):
        """Test circuit breaker as decorator."""
        from src.resilience.circuit_breaker import circuit_breaker

        call_count = 0

        @circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
        def test_function(should_fail=False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise Exception("Test failure")
            return "success"

        # Successful calls
        result = test_function(False)
        assert result == "success"
        assert call_count == 1
        
        # Failing calls to open circuit
        with pytest.raises(Exception):
            test_function(True)
        with pytest.raises(Exception):
            test_function(True)
        assert call_count == 3
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerOpen):
            test_function(False)
        assert call_count == 3  # Function not called due to open circuit


class TestResponseCache:
    """Test response caching functionality."""

    def test_cache_basic_operations(self):
        """Test basic cache set/get operations."""
        cache = ResponseCache(default_ttl=60)
        
        # Test cache miss
        result = cache.get("test_key")
        assert result is None
        
        # Test cache set and hit
        test_data = {"message": "test response", "timestamp": time.time()}
        cache.set("test_key", test_data)
        
        cached_result = cache.get("test_key")
        assert cached_result == test_data

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = ResponseCache(default_ttl=0.01)  # Very short TTL
        
        test_data = {"message": "expires soon"}
        cache.set("expire_key", test_data)
        
        # Should be available immediately
        assert cache.get("expire_key") == test_data
        
        # Wait for expiration
        time.sleep(0.02)
        assert cache.get("expire_key") is None

    def test_cache_custom_ttl(self):
        """Test cache with custom TTL per key."""
        cache = ResponseCache(default_ttl=60)
        
        # Set with custom TTL
        cache.set("custom_ttl_key", {"data": "custom"}, ttl=0.01)
        cache.set("default_ttl_key", {"data": "default"})  # Uses default TTL
        
        # Both should be available immediately
        assert cache.get("custom_ttl_key") is not None
        assert cache.get("default_ttl_key") is not None
        
        # Wait for custom TTL to expire
        time.sleep(0.02)
        assert cache.get("custom_ttl_key") is None  # Expired
        assert cache.get("default_ttl_key") is not None  # Still valid

    def test_cache_invalidation(self):
        """Test cache invalidation methods."""
        cache = ResponseCache(default_ttl=60)
        
        # Set multiple keys
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.set("key3", {"data": "value3"})

        # Test single key invalidation
        cache.invalidate("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

        # Test multiple individual invalidations
        cache.invalidate("key2")
        assert cache.get("key2") is None
        assert cache.get("key3") is not None

        # Test clear all
        cache.clear()
        assert cache.get("key3") is None

    def test_cache_thread_safety(self):
        """Test cache thread safety with concurrent access."""
        cache = ResponseCache(default_ttl=60)
        results = []
        
        def worker(worker_id):
            # Each worker sets and gets data
            key = f"worker_{worker_id}"
            data = {"worker": worker_id, "data": f"test_data_{worker_id}"}
            
            cache.set(key, data)
            result = cache.get(key)
            results.append(result)
        
        # Run multiple workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in futures:
                future.result()
        
        # Verify all workers got their data
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result["worker"] == i
            assert result["data"] == f"test_data_{i}"


class TestBulkheadIsolator:
    """Test bulkhead isolation for resource management."""

    def test_bulkhead_basic_execution(self):
        """Test basic bulkhead execution."""
        bulkhead = BulkheadIsolator(max_concurrent=2)
        
        execution_order = []
        
        def test_task(task_id):
            execution_order.append(f"start_{task_id}")
            time.sleep(0.01)  # Brief delay
            execution_order.append(f"end_{task_id}")
            return f"result_{task_id}"
        
        # Execute single task
        result = bulkhead.execute(test_task, 1)
        assert result == "result_1"
        assert "start_1" in execution_order
        assert "end_1" in execution_order

    def test_bulkhead_concurrency_limit(self):
        """Test bulkhead enforces concurrency limits."""
        bulkhead = BulkheadIsolator(max_concurrent=2, max_wait_time=0.1)
        
        execution_times = {}
        
        def slow_task(task_id):
            start_time = time.time()
            execution_times[f"start_{task_id}"] = start_time
            time.sleep(0.05)  # Simulate work
            end_time = time.time()
            execution_times[f"end_{task_id}"] = end_time
            return f"result_{task_id}"
        
        # Start multiple tasks concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(bulkhead.execute, slow_task, i)
                for i in range(4)
            ]
            
            results = []
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(f"error: {e}")
        
        # Should have some successful executions and some timeouts
        successful = [r for r in results if r.startswith("result_")]
        assert len(successful) >= 2  # At least the concurrent limit should succeed

    def test_bulkhead_timeout_handling(self):
        """Test bulkhead timeout handling."""
        bulkhead = BulkheadIsolator(max_concurrent=1, max_wait_time=0.01)
        
        def blocking_task():
            time.sleep(0.1)  # Longer than timeout
            return "should_not_complete"
        
        # First task will block
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(bulkhead.execute, blocking_task)
            time.sleep(0.005)  # Ensure first task starts
            
            # Second task should timeout
            future2 = executor.submit(bulkhead.execute, lambda: "quick_task")
            
            # Second task should timeout due to bulkhead limit
            with pytest.raises(Exception):  # Should raise timeout exception
                future2.result()


class TestFallbackChain:
    """Test fallback chain functionality."""

    def test_fallback_strategy_creation(self):
        """Test creating fallback chain."""
        def primary_func():
            return "primary_result"

        def fallback_func():
            return "fallback_result"

        chain = FallbackChain(name="test_chain")
        chain.add_fallback(primary_func, "primary")
        chain.add_fallback(fallback_func, "fallback")

        assert chain.name == "test_chain"
        assert len(chain.operations) == 2

    def test_fallback_chain_success_no_fallback(self):
        """Test fallback chain when primary succeeds."""
        def primary_success():
            return {"status": "success", "data": "primary_data"}

        def should_not_call():
            pytest.fail("Fallback should not be called")

        chain = FallbackChain(name="success_test")
        chain.add_fallback(primary_success, "primary")
        chain.add_fallback(should_not_call, "fallback")

        result = chain.execute()

        assert result["status"] == "success"
        assert result["data"] == "primary_data"

    def test_fallback_chain_primary_fails_fallback_succeeds(self):
        """Test fallback chain when primary fails but fallback succeeds."""
        def primary_failure():
            raise Exception("Primary function failed")

        def fallback_success():
            return {"status": "fallback_success", "data": "fallback_data"}

        chain = FallbackChain(name="fallback_test")
        chain.add_fallback(primary_failure, "primary")
        chain.add_fallback(fallback_success, "fallback")

        result = chain.execute()

        assert result["status"] == "fallback_success"
        assert result["data"] == "fallback_data"

    def test_fallback_chain_multiple_strategies(self):
        """Test fallback chain with multiple operations."""
        def operation1_fail():
            raise Exception("Operation 1 failed")

        def operation2_fail():
            raise Exception("Operation 2 failed")

        def operation3_success():
            return {"status": "operation3_success", "source": "operation3"}

        chain = FallbackChain(name="multi_test")
        chain.add_fallback(operation1_fail, "operation1")
        chain.add_fallback(operation2_fail, "operation2")
        chain.add_fallback(operation3_success, "operation3")

        result = chain.execute()

        assert result["status"] == "operation3_success"
        assert result["source"] == "operation3"

    def test_fallback_chain_all_strategies_fail(self):
        """Test fallback chain when all operations fail."""
        def always_fail():
            raise Exception("Always fails")

        chain = FallbackChain(name="all_fail_test")
        chain.add_fallback(always_fail, "operation1")
        chain.add_fallback(always_fail, "operation2")

        with pytest.raises(RuntimeError):  # FallbackChain raises RuntimeError when all fail
            chain.execute()

    def test_fallback_chain_with_retries(self):
        """Test fallback chain tries operations once (no built-in retries)."""
        call_count = 0

        def first_attempt_fails():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Attempt {call_count} failed")

        def fallback_success():
            return {"status": "fallback_success", "primary_attempts": call_count}

        chain = FallbackChain(name="retry_test")
        chain.add_fallback(first_attempt_fails, "primary")
        chain.add_fallback(fallback_success, "fallback")

        result = chain.execute()

        # Should fall back immediately after first failure
        assert result["status"] == "fallback_success"
        assert result["primary_attempts"] == 1  # Primary called once


class TestIntegratedResilience:
    """Test integrated resilience patterns working together."""

    def test_circuit_breaker_with_cache(self):
        """Test circuit breaker with cache fallback."""
        # Setup cache with fallback data
        cache = ResponseCache(default_ttl=60)
        cache.set("cached_response", {"status": "cached", "data": "fallback_data"})

        # Setup circuit breaker that will open quickly
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        failure_count = 0

        def unreliable_service():
            nonlocal failure_count
            failure_count += 1
            raise Exception("Service unavailable")

        def get_with_cache_fallback():
            try:
                return cb.call(unreliable_service)
            except (Exception, CircuitBreakerOpen):
                # Fallback to cache
                cached = cache.get("cached_response")
                if cached:
                    return cached
                raise Exception("No fallback available")

        # First call fails, circuit opens
        with pytest.raises(Exception):
            cb.call(unreliable_service)

        # Second call should use cache fallback due to open circuit
        result = get_with_cache_fallback()
        assert result["status"] == "cached"
        assert result["data"] == "fallback_data"

        # Verify circuit is open and function wasn't called again
        assert failure_count == 1

    def test_retry_with_bulkhead_and_cache(self):
        """Test retry logic with bulkhead isolation and cache."""
        cache = ResponseCache(default_ttl=60)
        bulkhead = BulkheadIsolator(max_concurrent=2, max_wait_time=1.0)
        
        attempt_count = 0
        
        def flaky_service(query):
            nonlocal attempt_count
            attempt_count += 1
            
            # Check cache first
            cache_key = f"service_{hash(query)}"
            cached = cache.get(cache_key)
            if cached:
                return cached
            
            # Simulate flaky service - fails first few times
            if attempt_count < 3:
                raise Exception(f"Service failed on attempt {attempt_count}")
            
            # Success - cache the result
            result = {"status": "success", "query": query, "attempt": attempt_count}
            cache.set(cache_key, result)
            return result
        
        # Execute with bulkhead isolation
        def execute_with_retry(query):
            for attempt in range(5):
                try:
                    return bulkhead.execute(flaky_service, query)
                except Exception as e:
                    if attempt == 4:  # Last attempt
                        raise e
                    time.sleep(exponential_backoff(attempt + 1, 0.01, 0.1, 2.0))
        
        # First execution should succeed after retries
        result1 = execute_with_retry("test_query_1")
        assert result1["status"] == "success"
        assert result1["attempt"] == 3
        
        # Reset attempt count for second query
        attempt_count = 0
        
        # Second execution with same query should hit cache
        result2 = execute_with_retry("test_query_1")
        assert result2["status"] == "success"
        assert result2["attempt"] == 3  # Same as cached
        assert attempt_count == 1  # Only one service call for cache check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])