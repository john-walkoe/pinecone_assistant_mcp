"""
Shared test fixtures for Pinecone Assistant MCP test suite.

This module provides common fixtures used across multiple test files,
reducing code duplication and ensuring consistent test data.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

import pytest

from src.config.config import Settings
from src.services.strategic_search import StrategySearchProcessor


# ==============================================================================
# Configuration Fixtures
# ==============================================================================

@pytest.fixture
def mock_settings() -> Settings:
    """
    Create mock settings for testing.

    Returns valid settings with test API key, host, and assistant name.
    Use this fixture when you need Settings object for testing without
    actual API credentials.

    Returns:
        Settings: Test settings with valid format but fake credentials
    """
    return Settings(
        pinecone_assistant_api_key="pcsk_test_key_12345678901234567890",
        pinecone_assistant_host="https://test.pinecone.io",
        pinecone_assistant_name="test-assistant",
        pinecone_assistant_model="gpt-4o"
    )


@pytest.fixture
def mock_env_vars() -> Dict[str, str]:
    """
    Provide test environment variables for configuration testing.

    Returns:
        Dict[str, str]: Environment variable dictionary suitable for patch.dict
    """
    return {
        'PINECONE_API_KEY': 'pcsk_test_key_12345678901234567890',
        'PINECONE_ASSISTANT_API_KEY': 'pcsk_test_key_12345678901234567890',
        'PINECONE_ASSISTANT_HOST': 'https://test.pinecone.io',
        'PINECONE_ASSISTANT_NAME': 'test-assistant'
    }


@pytest.fixture(autouse=True)
def mock_secure_storage():
    """
    Automatically mock secure storage for all tests.

    This fixture prevents tests from attempting to read from the system's
    secure credential storage, ensuring tests use only explicitly provided
    credentials via environment variables or Settings objects.

    autouse=True means this runs for every test automatically.
    """
    with patch('src.config.config.get_secure_api_key', return_value=None):
        yield


# ==============================================================================
# YAML Test Data Fixtures
# ==============================================================================

@pytest.fixture
def test_yaml_content() -> str:
    """
    Provide standard test YAML content for strategic search patterns.

    Returns:
        str: YAML content with test_domain and legal_domain patterns
    """
    return """
test_domain:
  searches:
    - name: "basic_search"
      query: "Basic search for {primary}"
      description: "Basic search pattern"
      enabled: true
    - name: "advanced_search"
      query: "Advanced {primary} with {key_terms}"
      description: "Advanced search pattern"
      enabled: true
    - name: "disabled_search"
      query: "Disabled {primary}"
      description: "Disabled search"
      enabled: false

legal_domain:
  searches:
    - name: "legal_analysis"
      query: "Legal analysis of {primary} under {key_terms}"
      description: "Legal analysis pattern"
      enabled: true
"""


@pytest.fixture
def temp_yaml_file(test_yaml_content: str):
    """
    Create a temporary YAML file for testing with automatic cleanup.

    Args:
        test_yaml_content: The YAML content fixture

    Yields:
        str: Path to temporary YAML file

    Note:
        File is automatically deleted after test completion.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(test_yaml_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except (FileNotFoundError, PermissionError):
        pass  # File may have been deleted by test


@pytest.fixture
def search_processor(tmp_path: Path) -> StrategySearchProcessor:
    """
    Create a test StrategySearchProcessor with mock YAML configuration.

    Args:
        tmp_path: pytest's tmp_path fixture for temporary directory

    Returns:
        StrategySearchProcessor: Processor initialized with test patterns
    """
    yaml_content = """
patent_law:
  searches:
    - name: "test_search"
      query: "Test query for {primary} and {key_terms}"
      description: "Test search pattern"
      enabled: true
    - name: "disabled_search"
      query: "Disabled {primary}"
      description: "Disabled search"
      enabled: false
"""

    yaml_file = tmp_path / "test_searches.yaml"
    yaml_file.write_text(yaml_content)

    return StrategySearchProcessor(yaml_path=yaml_file)


# ==============================================================================
# Mock API Response Fixtures
# ==============================================================================

@pytest.fixture
def mock_chat_response() -> Dict[str, Any]:
    """
    Provide a standard mock chat response from Pinecone Assistant API.

    Returns:
        Dict[str, Any]: Mock response with message, citations, and usage
    """
    return {
        "message": {
            "role": "assistant",
            "content": "Test response from assistant"
        },
        "finish_reason": "stop",
        "citations": [
            {
                "text": "Citation text",
                "source": "test_document.md"
            }
        ],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }


@pytest.fixture
def mock_context_response() -> Dict[str, Any]:
    """
    Provide a standard mock context response from Pinecone Assistant API.

    Returns:
        Dict[str, Any]: Mock response with chunks and usage
    """
    return {
        "chunks": [
            {
                "text": "Test document chunk 1",
                "score": 0.95,
                "metadata": {"source": "test.md", "page": 1}
            },
            {
                "text": "Test document chunk 2",
                "score": 0.88,
                "metadata": {"source": "test.md", "page": 2}
            }
        ],
        "usage": {"context_tokens": 200}
    }


@pytest.fixture
def mock_strategic_search_response() -> Dict[str, Any]:
    """
    Provide a standard mock strategic search response.

    Returns:
        Dict[str, Any]: Mock response with search results and aggregation
    """
    return {
        "results": [
            {
                "search_name": "test_search_1",
                "query": "Test query 1",
                "response": "Test response 1",
                "citations": [{"text": "Citation 1", "source": "doc1.md"}]
            },
            {
                "search_name": "test_search_2",
                "query": "Test query 2",
                "response": "Test response 2",
                "citations": [{"text": "Citation 2", "source": "doc2.md"}]
            }
        ],
        "aggregate_response": "Aggregated test response",
        "total_usage": {"input_tokens": 300, "output_tokens": 100}
    }


# ==============================================================================
# Mock Client Fixtures
# ==============================================================================

@pytest.fixture
def mock_assistant_client(mock_chat_response: Dict[str, Any],
                         mock_context_response: Dict[str, Any]) -> Mock:
    """
    Create a mock PineconeAssistantClient with standard responses.

    Args:
        mock_chat_response: Standard chat response fixture
        mock_context_response: Standard context response fixture

    Returns:
        Mock: Configured mock client ready for testing
    """
    mock_client = Mock()
    mock_client.chat.return_value = mock_chat_response
    mock_client.context.return_value = mock_context_response
    mock_client.test_connection.return_value = True

    return mock_client


@pytest.fixture
def mock_pinecone_assistant() -> Mock:
    """
    Create a mock Pinecone Assistant SDK object.

    Returns:
        Mock: Mock assistant object with chat method
    """
    mock_assistant = Mock()
    mock_assistant.chat.return_value = {
        "message": {"role": "assistant", "content": "Test response"},
        "finish_reason": "stop",
        "citations": [],
        "usage": {"input_tokens": 10, "output_tokens": 5}
    }

    return mock_assistant


# ==============================================================================
# Async Testing Support
# ==============================================================================

@pytest.fixture
def event_loop():
    """
    Provide event loop for async tests.

    This fixture is automatically used by pytest-asyncio for async test functions.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
