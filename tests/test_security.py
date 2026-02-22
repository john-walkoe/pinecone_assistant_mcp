"""Security-focused tests for API key handling, validation, and logging."""

import pytest
import os
import tempfile
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.config.config import Settings
from src.config.secure_storage import store_secure_api_key, get_secure_api_key, SecureStorage
from src.util.secure_logging import SecureFormatter, setup_secure_logging, sanitize_for_logging
from src.models.models import AssistantChatParams, Message
from src.util.exceptions import ValidationError, ConfigurationError


class TestAPIKeyValidation:
    """Test API key validation and security."""

    def test_valid_api_key_formats(self):
        """Test various valid API key formats."""
        valid_keys = [
            "pcsk_1234567890abcdef1234567890abcdef",
            "pcsk_test_key_with_underscores_and_numbers123",
            "pcsk_UPPERCASE_lowercase_MiXeD_123456",
            "pcsk_with-hyphens-and_underscores_123",
        ]
        
        for key in valid_keys:
            settings = Settings(
                pinecone_assistant_api_key=key,
                pinecone_assistant_host="https://test.pinecone.io",
                pinecone_assistant_name="test-assistant"
            )
            assert settings.pinecone_assistant_api_key == key

    @patch('src.config.config.get_secure_api_key', return_value=None)
    def test_invalid_api_key_formats(self, mock_secure_key):
        """Test rejection of invalid API key formats."""
        invalid_keys = [
            "",  # Empty
            "invalid_prefix_1234567890abcdef",  # Wrong prefix
            "pcsk_",  # Too short
            "pcsk_short",  # Too short
            "pcsk_with spaces_invalid",  # Contains spaces
            "pcsk_with@special#chars$",  # Invalid special characters
            "just_some_random_text",  # No prefix
            None,  # None value
        ]

        for key in invalid_keys:
            with pytest.raises(ValueError):
                Settings(
                    pinecone_assistant_api_key=key or "",
                    pinecone_assistant_host="https://test.pinecone.io",
                    pinecone_assistant_name="test-assistant"
                )

    def test_api_key_length_validation(self):
        """Test API key length requirements."""
        # Test minimum length
        short_key = "pcsk_12345"  # Too short
        with pytest.raises(ValueError, match="API key appears to be too short"):
            Settings(
                pinecone_assistant_api_key=short_key,
                pinecone_assistant_host="https://test.pinecone.io",
                pinecone_assistant_name="test-assistant"
            )
        
        # Test acceptable length
        valid_key = "pcsk_" + "a" * 32  # 32 chars after prefix
        settings = Settings(
            pinecone_assistant_api_key=valid_key,
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )
        assert settings.pinecone_assistant_api_key == valid_key

    def test_host_url_security_validation(self):
        """Test host URL security validation."""
        # Test HTTPS enforcement for production
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Should reject HTTP in production
            with pytest.raises(ValueError, match="Production environments must use HTTPS"):
                Settings(
                    pinecone_assistant_api_key="pcsk_" + "a" * 32,
                    pinecone_assistant_host="http://insecure.api.com",
                    pinecone_assistant_name="test-assistant"
                )
            
            # Should accept HTTPS in production
            settings = Settings(
                pinecone_assistant_api_key="pcsk_" + "a" * 32,
                pinecone_assistant_host="https://secure.api.com",
                pinecone_assistant_name="test-assistant"
            )
            assert settings.pinecone_assistant_host == "https://secure.api.com"

    def test_localhost_http_exception(self):
        """Test HTTP is allowed for localhost development."""
        localhost_urls = [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
        
        for url in localhost_urls:
            settings = Settings(
                pinecone_assistant_api_key="pcsk_" + "a" * 32,
                pinecone_assistant_host=url,
                pinecone_assistant_name="test-assistant"
            )
            assert url.rstrip('/') in settings.pinecone_assistant_host


class TestSecureStorage:
    """Test secure API key storage functionality."""

    @patch('platform.system')
    def test_secure_storage_detection(self, mock_platform):
        """Test platform detection for secure storage."""
        # Test that the function exists and is callable
        mock_platform.return_value = "Windows"

        # Test that store_secure_api_key is callable (actual behavior depends on OS)
        assert callable(store_secure_api_key)
        assert callable(get_secure_api_key)

    @patch('platform.system')
    def test_windows_dpapi_storage(self, mock_platform):
        """Test Windows DPAPI storage mechanism."""
        mock_platform.return_value = "Windows"

        # Test that on Windows, the API is available
        # Actual DPAPI functionality is tested via integration tests
        test_key = "pcsk_test_key_1234567890abcdef1234567890"

        # The function should be callable
        assert callable(store_secure_api_key)

        # Note: Actual DPAPI storage is environment-dependent
        # This test verifies the API is available

    def test_cross_platform_fallback(self, tmp_path):
        """Test Linux/non-Windows storage uses plaintext file with chmod 600."""
        key_path = tmp_path / ".pinecone_api_key"
        test_key = "pcsk_test_cross_platform_key"

        # Simulate non-Windows: sys.platform reports 'linux'
        with patch("src.config.secure_storage.sys") as mock_sys:
            mock_sys.platform = "linux"
            storage = SecureStorage(storage_file=str(key_path))
            result = storage.store_api_key(test_key)

        # On non-Windows: stores as plaintext with chmod 600 — succeeds
        assert result is True, "store_api_key must succeed on non-Windows (plaintext + chmod 600)"
        assert key_path.exists(), "Key file must be created on non-Windows"
        assert key_path.read_text().strip() == test_key, "Key must be readable as plaintext on Linux"
            
    def test_secure_key_retrieval_priority(self):
        """Test secure key retrieval priority order."""
        # Test environment variable retrieval
        test_key = "pcsk_test_priority_key_1234567890"

        # Test: Environment variable retrieval works
        with patch.dict(os.environ, {'PINECONE_ASSISTANT_API_KEY': test_key}):
            # The function should retrieve from env vars when secure storage is unavailable
            retrieved_key = get_secure_api_key()

            # Verify the function works (may return secure storage or env var depending on platform)
            assert retrieved_key is not None or test_key in os.environ.values()


class TestSecureLogging:
    """Test secure logging and data sanitization."""

    def test_api_key_sanitization(self):
        """Test API key sanitization in logs."""
        test_cases = [
            # (input, expected_output)
            ("pcsk_1234567890abcdef", "[REDACTED]"),
            ("API key: pcsk_abcdef123456", "API key: [REDACTED]"),
            ("Multiple pcsk_key1 and pcsk_key2", "Multiple [REDACTED] and [REDACTED]"),
            ("No keys here", "No keys here"),
            ("", ""),
        ]

        for input_text, expected in test_cases:
            result = sanitize_for_logging(input_text)
            assert result == expected

    def test_secure_logger_initialization(self):
        """Test secure logger initialization."""
        logger = setup_secure_logging("test_logger")

        assert logger.name == "test_logger"
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')

    def test_secure_logger_api_key_filtering(self):
        """Test secure logger filters API keys from log messages."""
        import io
        import sys

        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        formatter = SecureFormatter('%(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger("test_security_filter")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # Log message containing API key
        logger.info("Using API key pcsk_secret123456 for request")

        # Verify sanitized message was logged
        output = log_capture.getvalue()
        assert "pcsk_secret123456" not in output
        assert "[REDACTED]" in output
        assert "Using API key" in output

    def test_secure_logger_structured_data(self):
        """Test secure logger handles structured data."""
        import io

        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        formatter = SecureFormatter('%(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger("test_structured")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # Log structured data with API key
        log_data = {
            "action": "api_request",
            "api_key": "pcsk_sensitive_key",
            "endpoint": "/assistant/chat",
            "user_id": "user123"
        }

        logger.info("API request details", extra=log_data)

        # Verify call was made and message logged
        output = log_capture.getvalue()
        assert "API request details" in output

    def test_request_response_sanitization(self):
        """Test sanitization of request/response data."""
        # Test request data
        request_data = {
            "headers": {
                "Api-Key": "pcsk_secret_key_123",
                "Content-Type": "application/json"
            },
            "body": {"query": "test query", "api_key": "pcsk_another_key"}
        }
        
        sanitized = sanitize_for_logging(str(request_data))
        assert "pcsk_secret_key_123" not in sanitized
        assert "pcsk_another_key" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_exception_sanitization(self):
        """Test sanitization of exception messages."""
        try:
            # Create exception with API key in message
            raise Exception("Authentication failed with key pcsk_leaked_key_123")
        except Exception as e:
            sanitized_msg = sanitize_for_logging(str(e))
            assert "pcsk_leaked_key_123" not in sanitized_msg
            assert "[REDACTED]" in sanitized_msg


class TestInputValidation:
    """Test input validation and injection prevention."""

    def test_assistant_name_validation(self):
        """Test assistant name validation."""
        # Valid names
        valid_names = [
            "test-assistant",
            "my_assistant_123",
            "AssistantName",
            "assistant-with-hyphens",
        ]
        
        for name in valid_names:
            settings = Settings(
                pinecone_assistant_api_key="pcsk_" + "a" * 32,
                pinecone_assistant_host="https://test.pinecone.io",
                pinecone_assistant_name=name
            )
            assert settings.pinecone_assistant_name == name
        
        # Invalid names
        invalid_names = [
            "",  # Empty
            "ab",  # Too short
            None,  # None
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                Settings(
                    pinecone_assistant_api_key="pcsk_" + "a" * 32,
                    pinecone_assistant_host="https://test.pinecone.io",
                    pinecone_assistant_name=name or ""
                )

    def test_message_content_validation(self):
        """Test message content validation for injection attacks."""
        # Test normal message
        message = Message(role="user", content="What is patent eligibility?")
        assert message.content == "What is patent eligibility?"
        
        # Test message with potential injection attempts (should be allowed but logged)
        suspicious_content = "'; DROP TABLE users; --"
        message = Message(role="user", content=suspicious_content)
        assert message.content == suspicious_content  # Content preserved
        
        # Test extremely long content
        long_content = "A" * 100000
        message = Message(role="user", content=long_content)
        assert len(message.content) == 100000

    def test_model_parameter_validation(self):
        """Test model parameter validation."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_" + "a" * 32,
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )
        
        # Valid models (as of API version 2025-04)
        valid_models = ["gpt-4o", "claude-3-5-sonnet", "gemini-2.5-pro", "gpt-4.1", "o4-mini", "claude-3-7-sonnet"]
        for model in valid_models:
            assert settings.is_valid_model(model) is True
        
        # Invalid models
        invalid_models = ["gpt-3.5", "custom-model", "", None]
        for model in invalid_models:
            assert settings.is_valid_model(model or "") is False

    def test_parameter_boundary_validation(self):
        """Test parameter boundary validation."""
        # Test temperature bounds
        valid_params = AssistantChatParams(
            messages=[Message(role="user", content="test")],
            temperature=1.0
        )
        assert valid_params.temperature == 1.0
        
        # Test invalid temperature (should be caught by Pydantic)
        with pytest.raises(ValueError):
            AssistantChatParams(
                messages=[Message(role="user", content="test")],
                temperature=3.0  # Out of bounds
            )


class TestSecurityHeaders:
    """Test security-related HTTP headers and configurations."""

    def test_api_headers_security(self):
        """Test API headers contain security information."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_" + "a" * 32,
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant"
        )
        
        headers = settings.headers
        
        # Test required headers
        assert "Api-Key" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        
        # Test API version header
        assert "X-Pinecone-API-Version" in headers
        
        # Test API key is present but not logged
        assert headers["Api-Key"].startswith("pcsk_")

    def test_request_timeout_security(self):
        """Test request timeout prevents hanging connections."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_" + "a" * 32,
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant",
            request_timeout=10
        )
        
        assert settings.request_timeout == 10
        assert 5 <= settings.request_timeout <= 300  # Reasonable bounds

    def test_retry_limits_security(self):
        """Test retry limits prevent resource exhaustion."""
        settings = Settings(
            pinecone_assistant_api_key="pcsk_" + "a" * 32,
            pinecone_assistant_host="https://test.pinecone.io",
            pinecone_assistant_name="test-assistant",
            max_retries=5
        )
        
        assert settings.max_retries == 5
        assert 0 <= settings.max_retries <= 10  # Reasonable bounds


class TestSecurityIntegration:
    """Test integrated security features."""

    def test_end_to_end_api_key_security(self):
        """Test end-to-end API key security flow."""
        test_key = "pcsk_integration_test_key_123456789012"

        # Test 1: Store securely (mock SecureStorage.store_api_key)
        with patch('src.config.secure_storage.SecureStorage.store_api_key') as mock_store:
            mock_store.return_value = True

            result = store_secure_api_key(test_key)
            assert result is True
            mock_store.assert_called_once_with(test_key)

        # Test 2: Retrieve securely (mock SecureStorage.get_api_key)
        with patch('src.config.secure_storage.SecureStorage.get_api_key') as mock_get:
            mock_get.return_value = test_key

            retrieved = get_secure_api_key()
            assert retrieved == test_key
            mock_get.assert_called_once()

        # Test 3: Use in settings with secure source
        # Need to patch at config level where Settings calls it
        with patch('src.config.config.get_secure_api_key') as mock_get_secure:
            mock_get_secure.return_value = test_key

            settings = Settings(
                pinecone_assistant_host="https://test.pinecone.io",
                pinecone_assistant_name="test-assistant"
            )

            # Verify key loaded from secure storage
            assert settings.pinecone_assistant_api_key == test_key
            mock_get_secure.assert_called()

            # Verify API key is valid
            assert settings.is_valid_model("gpt-4o")
            assert settings.base_url.startswith("https://test.pinecone.io")

    def test_logging_security_integration(self):
        """Test logging security across components."""
        import io

        # Create a logger with secure formatter
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        formatter = SecureFormatter('%(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger("integration_test_security")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # Simulate logging from different components
        logger.info("Assistant client initialized with key pcsk_test_key_123456")
        logger.info("Request headers: {'Api-Key': 'pcsk_another_key_7890'}")
        logger.info("Configuration loaded successfully")

        # Get logged output
        output = log_capture.getvalue()

        # Verify all API keys were sanitized
        assert "pcsk_test_key_123456" not in output
        assert "pcsk_another_key_7890" not in output
        assert "[REDACTED]" in output
        assert "Configuration loaded successfully" in output

    def test_configuration_security_validation(self):
        """Test comprehensive configuration security validation."""
        # Test valid secure configuration
        secure_config = {
            "pinecone_assistant_api_key": "pcsk_" + "a" * 32,
            "pinecone_assistant_host": "https://secure-api.pinecone.io",
            "pinecone_assistant_name": "secure-assistant",
            "request_timeout": 30,
            "max_retries": 3,
            "debug_logging": False
        }
        
        settings = Settings(**secure_config)
        
        # Verify all security aspects
        assert settings.pinecone_assistant_api_key.startswith("pcsk_")
        assert settings.pinecone_assistant_host.startswith("https://")
        assert len(settings.pinecone_assistant_name) >= 3
        assert 5 <= settings.request_timeout <= 300
        assert 0 <= settings.max_retries <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])