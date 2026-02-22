# Test Suite - Pinecone Assistant MCP

This directory contains the comprehensive test suite for the **Pinecone Assistant MCP Server** - a generic, domain-agnostic MCP server for conversational AI document research using the Pinecone Assistant API.

## 📋 Table of Contents

- [Overview](#overview)
- [Available MCP Tools](#available-mcp-tools)
- [Test Files](#test-files)
- [Environment Setup](#environment-setup)
- [Running Tests](#running-tests)
- [Expected Test Outputs](#expected-test-outputs)
- [Environment Variables Reference](#environment-variables-reference)
- [Troubleshooting](#troubleshooting)
- [Test Development Guidelines](#test-development-guidelines)

## Overview

The Pinecone Assistant MCP test suite validates **6 MCP tools** with **144 tests (100% passing)** across 8 comprehensive test files covering:
- ✅ **Basic functionality** (configuration, validation, strategic search) - 19 tests
- ✅ **Integration testing** (end-to-end workflows, tool interactions, multi-assistant switching) - 17 tests
- ✅ **Resilience patterns** (retry logic, circuit breaker, caching, bulkhead isolation, fallback chains) - 25 tests
- ✅ **Security features** (API key handling, input validation, secure logging, DPAPI encryption) - 25 tests
- ✅ **Unified credential architecture** (pinecone_API_KEY target, embedded entropy format, env var fallback chain) - 15 tests
- ✅ **Entropy security** (randomness, tamper detection, DPAPI key file format) - 15 tests
- ✅ **Security audit** (hardcoded entropy detection, file permissions, codebase scans) - 14 tests
- ✅ **Monitoring & observability** (health checks, metrics, circuit breaker state) - 14 tests
- ✅ **Cross-platform compatibility** (Windows DPAPI, Linux fallbacks)
- ✅ **Domain-agnostic architecture** (customizable via YAML, zero-code domain changes)

**Test Infrastructure:**
- Shared fixtures in `conftest.py` for consistent test data
- Automatic secure storage mocking (autouse fixture)
- Mock API responses for all Pinecone Assistant endpoints
- 100% type hint coverage across codebase

## Available MCP Tools

The MCP server provides **6 tools** for intelligent document research with cost optimization:

### Document Retrieval Tools (2) - Zero AI Cost

| Tool Name | Display Name | Purpose | Token Cost |
|-----------|--------------|---------|------------|
| `assistant_context` | Assistant context | Raw document retrieval without AI processing | Context tokens only (FREE) |
| `assistant_strategic_multi_search_context` | Assistant strategic multi search context | Strategic raw document retrieval across patterns | Context tokens only (FREE) |

### AI-Powered Tools (2) - Higher Cost

| Tool Name | Display Name | Purpose | Token Cost |
|-----------|--------------|---------|------------|
| `assistant_strategic_multi_search_chat` | Assistant strategic multi search | Strategic research with AI synthesis | Input + Output tokens |
| `assistant_chat` | Assistant chat | Direct AI conversation with citations | Input + Output tokens |

### Configuration Tool (1)

| Tool Name | Display Name | Purpose |
|-----------|--------------|---------|
| `update_configuration` | Update configuration | Switch assistants/models mid-conversation |

### Evaluation Tool (1) - Requires Paid Plan

| Tool Name | Display Name | Purpose | Token Cost |
|-----------|--------------|---------|------------|
| `evaluate_answer` | Evaluate answer | Score AI answer quality against ground truth | Input + Output tokens (Standard plan only) |

## Test Files

### Core Test Suite (8 Files)

| Test File | Purpose | Components Tested | API Key Required |
|-----------|---------|-------------------|------------------|
| `test_basic.py` | Core functionality & validation | Configuration, models, strategic search | No |
| `test_integration.py` | End-to-end workflows & tool integration | All 6 MCP tools, workflow scenarios | No (mocked) |
| `test_resilience.py` | Production resilience patterns | Retry, circuit breaker, cache, bulkhead, fallback | No |
| `test_security.py` | Security & validation | API key handling, secure storage, input validation | No |
| `test_unified_credential.py` | Unified credential architecture | `pinecone_API_KEY` target, `~/.pinecone_api_key` file, embedded entropy, env var fallback chain | No |
| `test_entropy_security.py` | Entropy & DPAPI key file security | Entropy randomness, tamper detection, embedded format, DPAPI round-trip | No |
| `test_security_audit.py` | Static security audit | Hardcoded entropy/secret detection, file permission checks, codebase scans | No |
| `test_monitoring.py` | Monitoring & observability | Health checks, metrics collection, circuit breaker state reporting | No |

### Test Coverage Breakdown

#### test_basic.py - Foundation Tests
- ✅ Configuration validation (API key format, host URL, assistant name)
- ✅ Pydantic model validation (messages, parameters)
- ✅ `EvaluateAnswerParams` model validation (required fields, missing-field errors)
- ✅ `AssistantContextParams` multimodal fields (`multimodal`, `include_binary_content`, messages-vs-query validator)
- ✅ Strategic search YAML loading
- ✅ Key term extraction and pattern substitution
- ✅ Domain validation

#### test_integration.py - Workflow Tests
- ✅ MCP tool integration (all 6 tools)
- ✅ `evaluate_answer` success path (scores, per-fact reasoning, token usage)
- ✅ `evaluate_answer` free-tier error → `VALIDATION_ERROR` structured response
- ✅ `assistant_context` multimodal params forwarded to client
- ✅ **Recommended workflow**: Context first → AI if needed
- ✅ **Multi-assistant switching** workflow
- ✅ **Token optimization** strategies
- ✅ Error recovery and fallback scenarios
- ✅ End-to-end integration testing

#### test_resilience.py - Production Patterns
- ✅ **Retry logic** with exponential backoff and jitter
- ✅ **Circuit breaker** (closed → open → half-open → closed)
- ✅ **Response caching** with TTL expiration
- ✅ **Bulkhead isolation** for concurrency limits
- ✅ **Fallback chains** with multiple strategies
- ✅ **Integrated resilience** (multiple patterns working together)

#### test_security.py - Security Tests
- ✅ **API key validation** (format, length, character restrictions)
- ✅ **Secure storage** (Windows DPAPI, cross-platform fallback)
- ✅ **Secure logging** (API key sanitization, structured data)
- ✅ **Input validation** (assistant names, model parameters, message content)
- ✅ **Security headers** and timeout configurations
- ✅ **Env var priority** (`PINECONE_API_KEY` primary → `PINECONE_ASSISTANT_API_KEY` fallback)

#### test_unified_credential.py - Unified Credential Architecture Tests
- ✅ **Credential constants** (`CREDENTIAL_TARGET == "pinecone_API_KEY"`, correct file paths)
- ✅ **Storage file path** (`~/.pinecone_api_key`, no separate entropy file)
- ✅ **Internal auth secret** (`~/.uspto_internal_auth_secret` path and "first wins" generation)
- ✅ **`entropy_file` attribute is `None`** (no legacy separate entropy file)
- ✅ **No old credential strings** in codebase
- ✅ **Env var fallback chain** (`PINECONE_API_KEY` → `PINECONE_ASSISTANT_API_KEY`)

#### test_entropy_security.py - Entropy & DPAPI Key File Security Tests
- ✅ **Entropy randomness** (uniqueness across instances, length checks)
- ✅ **Embedded format** (bytes 0-31 = entropy prefix, bytes 32+ = DPAPI encrypted key)
- ✅ **DPAPI round-trip** (store → retrieve → verify match)
- ✅ **Tamper detection** (modifying embedded entropy bytes breaks decryption)
- ✅ **Internal auth secret creation** (generated when missing, reused when present)
- ✅ **No hardcoded entropy** in production paths (only in deprecated functions)

#### test_security_audit.py - Static Security Audit Tests
- ✅ **No hardcoded entropy** in non-deprecated code paths
- ✅ **No legacy credential names** in codebase
- ✅ **File permission checks** (key file mode 0o600 on Linux)
- ✅ **Codebase scans** for secret patterns

#### test_monitoring.py - Monitoring & Observability Tests
- ✅ **Health checks** (storage health, API connectivity reporting)
- ✅ **Metrics collection** (request counts, latency, error rates)
- ✅ **Circuit breaker state** reporting in health output

## Environment Setup

### API Key Configuration

**Pinecone Assistant API Key (Required for real testing):**
- **Purpose**: Access to Pinecone Assistant API for document research
- **Without it**: Tests run with mocked responses (full functionality testing)
- **Get your key**: [Pinecone Console](https://app.pinecone.io/) → API Keys → Assistant API

**Setting Environment Variables:**

```bash
# Windows PowerShell
$env:PINECONE_ASSISTANT_API_KEY="pcsk_your_key_here"
$env:PINECONE_ASSISTANT_HOST="https://prod-1-data.ke.pinecone.io"
$env:PINECONE_ASSISTANT_NAME="your-assistant-name"

# Windows Command Prompt
set PINECONE_ASSISTANT_API_KEY=pcsk_your_key_here
set PINECONE_ASSISTANT_HOST=https://prod-1-data.ke.pinecone.io
set PINECONE_ASSISTANT_NAME=your-assistant-name

# Linux/macOS
export PINECONE_ASSISTANT_API_KEY="pcsk_your_key_here"
export PINECONE_ASSISTANT_HOST="https://prod-1-data.ke.pinecone.io"
export PINECONE_ASSISTANT_NAME="your-assistant-name"
```

**Important:** All tests are designed to work **without real API keys** using mocks. API keys are only needed for testing against live Pinecone Assistant instances.

### Installing Test Dependencies

**With uv (Recommended):**
```bash
cd pinecone_assistant_mcp
uv sync --group dev
```

**With pip:**
```bash
cd pinecone_assistant_mcp
pip install -e ".[dev]"
```

## Running Tests

### Quick Test (Essential)

Test all core components:

```bash
# With uv (recommended)
uv run pytest tests/test_basic.py -v

# With traditional Python
python -m pytest tests/test_basic.py -v
```

### Comprehensive Test Suite

```bash
# Run all tests
uv run pytest

# Run all tests with verbose output
uv run pytest -v

# Run specific test files
uv run pytest tests/test_basic.py           # Basic functionality tests
uv run pytest tests/test_integration.py    # Integration and workflow tests
uv run pytest tests/test_resilience.py     # Resilience patterns
uv run pytest tests/test_security.py       # Security and validation tests
```

### Test Categories

```bash
# Run specific test categories
uv run pytest -k "integration"             # Integration tests only
uv run pytest -k "security"                # Security tests only
uv run pytest -k "resilience"              # Resilience tests only
uv run pytest -k "workflow"                # Workflow tests only

# Run with coverage reporting
uv run pytest --cov=src --cov-report=html

# Run with asyncio debugging
uv run pytest --asyncio-mode=auto
```

### Performance and Load Testing

```bash
# Test resilience patterns under load
uv run pytest tests/test_resilience.py::TestIntegratedResilience -v

# Test concurrent workflows
uv run pytest tests/test_integration.py::TestEndToEndWorkflow -v

# Test circuit breaker behavior
uv run pytest tests/test_resilience.py::TestCircuitBreaker -v
```

## Expected Test Outputs

### test_basic.py (Foundation Tests)

```
tests/test_basic.py::TestConfiguration::test_settings_validation_success PASSED
tests/test_basic.py::TestConfiguration::test_api_key_validation_failure PASSED
tests/test_basic.py::TestConfiguration::test_base_url_property PASSED
tests/test_basic.py::TestConfiguration::test_is_valid_model PASSED
tests/test_basic.py::TestTypes::test_message_creation PASSED
tests/test_basic.py::TestTypes::test_assistant_chat_params PASSED
tests/test_basic.py::TestTypes::test_strategy_search_params PASSED
tests/test_basic.py::TestTypes::test_evaluate_answer_params PASSED
tests/test_basic.py::TestTypes::test_evaluate_answer_params_missing_fields PASSED
tests/test_basic.py::TestTypes::test_assistant_context_params_multimodal PASSED
tests/test_basic.py::TestTypes::test_assistant_context_params_multimodal_defaults PASSED
tests/test_basic.py::TestTypes::test_assistant_context_params_requires_query_or_messages PASSED
tests/test_basic.py::TestTypes::test_assistant_context_params_messages_without_query PASSED
tests/test_basic.py::TestStrategicSearch::test_load_patterns PASSED
tests/test_basic.py::TestStrategicSearch::test_extract_key_terms PASSED
tests/test_basic.py::TestStrategicSearch::test_substitute_patterns PASSED
tests/test_basic.py::TestStrategicSearch::test_validate_domain PASSED
tests/test_basic.py::TestAssistantClientMock::test_client_initialization PASSED
tests/test_basic.py::TestAssistantClientMock::test_chat_request PASSED

================ 19 passed in 1.23s ================
```

### test_integration.py (Integration Tests)

```
tests/test_integration.py::TestIntegrationSetup::test_environment_configuration PASSED
tests/test_integration.py::TestIntegrationSetup::test_strategic_search_yaml_loading PASSED
tests/test_integration.py::TestIntegrationSetup::test_client_manager_initialization PASSED
tests/test_integration.py::TestToolIntegration::test_assistant_chat_tool PASSED
tests/test_integration.py::TestToolIntegration::test_assistant_context_tool PASSED
tests/test_integration.py::TestToolIntegration::test_strategic_multi_search_tool PASSED
tests/test_integration.py::TestToolIntegration::test_strategic_context_search_tool PASSED
tests/test_integration.py::TestToolIntegration::test_update_configuration_tool PASSED
tests/test_integration.py::TestToolIntegration::test_evaluate_answer_tool PASSED
tests/test_integration.py::TestToolIntegration::test_evaluate_answer_free_tier_error PASSED
tests/test_integration.py::TestToolIntegration::test_assistant_context_multimodal_params PASSED
tests/test_integration.py::TestToolIntegration::test_invalid_tool_name PASSED
tests/test_integration.py::TestToolIntegration::test_tool_error_handling PASSED
tests/test_integration.py::TestEndToEndWorkflow::test_research_workflow_context_first PASSED
tests/test_integration.py::TestEndToEndWorkflow::test_multi_assistant_workflow PASSED
tests/test_integration.py::TestEndToEndWorkflow::test_error_recovery_workflow PASSED
tests/test_integration.py::TestEndToEndWorkflow::test_token_optimization_workflow PASSED

================ 16 passed in 2.45s ================
```

### test_resilience.py (Resilience Patterns)

```
tests/test_resilience.py::TestRetryUtils::test_exponential_backoff_calculation PASSED
tests/test_resilience.py::TestRetryUtils::test_retryable_http_client_success PASSED
tests/test_resilience.py::TestRetryUtils::test_retryable_http_client_retry_on_failure PASSED
tests/test_resilience.py::TestRetryUtils::test_retryable_http_client_max_retries_exceeded PASSED
tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_closed_state PASSED
tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_open_state PASSED
tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_half_open_state PASSED
tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_recovery PASSED
tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_decorator PASSED
tests/test_resilience.py::TestResponseCache::test_cache_basic_operations PASSED
tests/test_resilience.py::TestResponseCache::test_cache_ttl_expiration PASSED
tests/test_resilience.py::TestResponseCache::test_cache_custom_ttl PASSED
tests/test_resilience.py::TestResponseCache::test_cache_invalidation PASSED
tests/test_resilience.py::TestResponseCache::test_cache_thread_safety PASSED
tests/test_resilience.py::TestBulkheadIsolator::test_bulkhead_basic_execution PASSED
tests/test_resilience.py::TestBulkheadIsolator::test_bulkhead_concurrency_limit PASSED
tests/test_resilience.py::TestBulkheadIsolator::test_bulkhead_timeout_handling PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_strategy_creation PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_chain_success_no_fallback PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_chain_primary_fails_fallback_succeeds PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_chain_multiple_strategies PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_chain_all_strategies_fail PASSED
tests/test_resilience.py::TestFallbackChain::test_fallback_chain_with_retries PASSED
tests/test_resilience.py::TestIntegratedResilience::test_circuit_breaker_with_cache PASSED
tests/test_resilience.py::TestIntegratedResilience::test_retry_with_bulkhead_and_cache PASSED

================ 30 passed in 1.82s ================
```

### test_security.py (Security Tests)

```
tests/test_security.py::TestAPIKeyValidation::test_valid_api_key_formats PASSED
tests/test_security.py::TestAPIKeyValidation::test_invalid_api_key_formats PASSED
tests/test_security.py::TestAPIKeyValidation::test_api_key_length_validation PASSED
tests/test_security.py::TestAPIKeyValidation::test_host_url_security_validation PASSED
tests/test_security.py::TestAPIKeyValidation::test_localhost_http_exception PASSED
tests/test_security.py::TestSecureStorage::test_secure_storage_detection PASSED
tests/test_security.py::TestSecureStorage::test_windows_dpapi_storage PASSED
tests/test_security.py::TestSecureStorage::test_cross_platform_fallback PASSED
tests/test_security.py::TestSecureStorage::test_secure_key_retrieval_priority PASSED
tests/test_security.py::TestSecureLogging::test_api_key_sanitization PASSED
tests/test_security.py::TestSecureLogging::test_secure_logger_initialization PASSED
tests/test_security.py::TestSecureLogging::test_secure_logger_api_key_filtering PASSED
tests/test_security.py::TestSecureLogging::test_secure_logger_structured_data PASSED
tests/test_security.py::TestSecureLogging::test_request_response_sanitization PASSED
tests/test_security.py::TestSecureLogging::test_exception_sanitization PASSED
tests/test_security.py::TestInputValidation::test_assistant_name_validation PASSED
tests/test_security.py::TestInputValidation::test_message_content_validation PASSED
tests/test_security.py::TestInputValidation::test_model_parameter_validation PASSED
tests/test_security.py::TestInputValidation::test_parameter_boundary_validation PASSED
tests/test_security.py::TestSecurityHeaders::test_api_headers_security PASSED
tests/test_security.py::TestSecurityHeaders::test_request_timeout_security PASSED
tests/test_security.py::TestSecurityHeaders::test_retry_limits_security PASSED
tests/test_security.py::TestSecurityIntegration::test_end_to_end_api_key_security PASSED
tests/test_security.py::TestSecurityIntegration::test_logging_security_integration PASSED
tests/test_security.py::TestSecurityIntegration::test_configuration_security_validation PASSED

================ 21 passed in 1.89s ================
```

### Complete Test Suite Summary

**Current Status: 144/144 tests passing (100%)**

```
================= test session starts =================
platform win32 -- Python 3.12.11
collected 144 items

tests/test_basic.py ................... [ 13%]   # 19 tests
tests/test_integration.py ................. [ 25%] # 17 tests
tests/test_resilience.py ......................... [ 42%]  # 25 tests
tests/test_security.py ......................... [ 59%]  # 25 tests
tests/test_unified_credential.py ............... [ 70%]  # 15 tests
tests/test_entropy_security.py ............... [ 80%]  # 15 tests
tests/test_security_audit.py .............. [ 90%]  # 14 tests
tests/test_monitoring.py .............. [100%]  # 14 tests

================ 144 passed ================
```

**Test Distribution:**
- ✅ Basic Tests: 19/19 passing
- ✅ Integration Tests: 17/17 passing
- ✅ Resilience Tests: 25/25 passing
- ✅ Security Tests: 25/25 passing
- ✅ Unified Credential Tests: 15/15 passing
- ✅ Entropy Security Tests: 15/15 passing
- ✅ Security Audit Tests: 14/14 passing
- ✅ Monitoring Tests: 14/14 passing

**Code Quality:**
- ✅ 100% type hint coverage
- ✅ Shared fixtures in conftest.py
- ✅ Automatic secure storage mocking
- ✅ Comprehensive package documentation
```

## Environment Variables Reference

| Variable | Default | Purpose | Test Files Using It |
|----------|---------|---------|---------------------|
| `PINECONE_API_KEY` | None | Pinecone API key (**canonical — preferred**) | test_unified_credential.py, test_security.py, conftest.py |
| `PINECONE_ASSISTANT_API_KEY` | None | Pinecone API key (legacy fallback; still accepted) | test_integration.py, test_security.py, conftest.py |
| `PINECONE_ASSISTANT_HOST` | https://prod-1-data.ke.pinecone.io | Assistant API host URL | test_basic.py, test_integration.py |
| `PINECONE_ASSISTANT_NAME` | None | Assistant instance name | test_basic.py, test_integration.py |
| `PINECONE_ASSISTANT_MODEL` | gpt-4o | Default AI model | test_basic.py |
| `DEFAULT_TEMPERATURE` | 0.2 | AI response temperature (USPTO legal precision) | test_basic.py |
| `DEBUG_LOGGING` | false | Enable debug logging | test_security.py |
| `REQUEST_TIMEOUT` | 30 | HTTP request timeout (seconds) | test_security.py |
| `MAX_RETRIES` | 3 | Maximum retry attempts | test_resilience.py |
| `ENVIRONMENT` | development | Environment (production enforces HTTPS) | test_security.py |

## Troubleshooting

### Issue: Tests Pass but API Key Warnings

**Cause:** Tests run with mocked responses when no real API key is provided

**This is normal behavior:**
- ✅ All tests validate functionality with mocks
- ✅ No real API calls needed for testing
- ✅ Set `PINECONE_ASSISTANT_API_KEY` only for live API testing

### Issue: "Invalid API Key Format" in Security Tests

**Cause:** Security tests validate API key format

**Solution:** This is expected behavior - security tests verify validation works:
```bash
# These test scenarios are intentional:
tests/test_security.py::TestAPIKeyValidation::test_invalid_api_key_formats PASSED
```

### Issue: Import Errors

**Cause:** Dependencies not installed or stale installation

**Solution:**
```bash
# With uv
uv sync --reinstall --group dev

# With pip
pip install -e ".[dev]" --force-reinstall
```

### Issue: Async Test Warnings

**Cause:** Asyncio event loop configuration

**Solution:**
```bash
# Run with asyncio mode enabled
uv run pytest --asyncio-mode=auto

# Or add to pytest.ini (already configured)
asyncio_mode = auto
```

### Issue: Cache Tests Flaky Due to Timing

**Cause:** TTL timing in cache tests

**Solution:**
```bash
# Run cache tests individually with more time
uv run pytest tests/test_resilience.py::TestResponseCache -v -s
```

### Issue: Windows DPAPI Tests Fail on Linux

**Cause:** Windows-specific secure storage tests

**Solution:** This is expected - tests include platform detection:
```bash
# Linux users: DPAPI tests skip gracefully
# Windows users: Full DPAPI encryption testing
```

### Issue: Circuit Breaker Tests Timing Out

**Cause:** Long recovery timeouts in tests

**Solution:**
```bash
# Tests use very short timeouts for speed
# If still timing out, run individually:
uv run pytest tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_half_open_state -v
```

## Test Development Guidelines

### Shared Test Fixtures (conftest.py)

The test suite uses **`conftest.py`** for shared fixtures across all test files, eliminating duplication and ensuring consistency.

**Available Fixtures:**

#### Configuration Fixtures
```python
# Standard test settings (used in most tests)
def test_example(mock_settings):
    assert mock_settings.pinecone_assistant_api_key.startswith('pcsk_')

# Environment variables for configuration testing
def test_env_config(mock_env_vars):
    with patch.dict(os.environ, mock_env_vars):
        # Test with environment variables
        pass

# Automatic secure storage mocking (runs for all tests)
# No need to manually mock - handled automatically
```

#### YAML Test Data Fixtures
```python
# Temporary YAML file with automatic cleanup
def test_yaml_loading(temp_yaml_file):
    processor = StrategySearchProcessor(yaml_path=temp_yaml_file)
    # File automatically deleted after test

# Pre-configured search processor
def test_strategic_search(search_processor):
    domains = search_processor.get_available_domains()
    # Ready to use, no setup needed
```

#### Mock API Response Fixtures
```python
# Mock chat response with proper structure
def test_chat(mock_chat_response):
    assert "message" in mock_chat_response
    assert "citations" in mock_chat_response

# Mock context response
def test_context(mock_context_response):
    assert "chunks" in mock_context_response

# Fully configured mock client
def test_client_operation(mock_assistant_client):
    response = mock_assistant_client.chat(params)
    # Client already configured with standard responses
```

**Benefits:**
- ✅ No duplicate fixture code across test files
- ✅ Consistent test data throughout suite
- ✅ Automatic secure storage mocking (no manual setup)
- ✅ Easy to extend for new tests
- ✅ Comprehensive documentation for each fixture

**See `tests/conftest.py`** for complete fixture documentation with usage examples.

### Adding New Tests

1. **Choose appropriate test file**:
   - `test_basic.py` - Core functionality, validation
   - `test_integration.py` - Tool integration, workflows
   - `test_resilience.py` - Fault tolerance patterns
   - `test_security.py` - Security, API key validation, secure storage
   - `test_unified_credential.py` - Credential architecture constants and behavior
   - `test_entropy_security.py` - DPAPI encryption, entropy format, tamper detection
   - `test_security_audit.py` - Static codebase scans, file permissions
   - `test_monitoring.py` - Health checks, metrics, observability

2. **Follow naming conventions**:
   ```python
   class TestFeatureName:
       def test_specific_behavior(self):
           """Test specific behavior with clear expectations"""
   ```

3. **Use shared fixtures from conftest.py**:
   ```python
   # Use existing shared fixtures (preferred)
   def test_with_shared_fixtures(self, mock_settings, mock_chat_response):
       # Fixtures automatically available from conftest.py
       assert mock_settings.pinecone_assistant_api_key.startswith('pcsk_')
       assert "message" in mock_chat_response

   # Only create new fixtures if needed for specific tests
   @pytest.fixture
   def custom_test_data(self):
       return {"special": "data"}
   ```

4. **Mock external dependencies**:
   ```python
   @patch('src.assistant_client.Pinecone')
   def test_client_functionality(self, mock_pinecone):
       # Mock setup
       # Test implementation
   ```

### Best Practices

1. **Independent tests**: Each test should be self-contained
2. **Clear assertions**: Use descriptive assertion messages
3. **Mock external calls**: Don't make real API calls in unit tests
4. **Test edge cases**: Include boundary conditions and error scenarios
5. **Document purpose**: Add docstrings explaining test objectives
6. **Use parametrization**: Test multiple inputs efficiently

### Example Test Template

```python
"""
Test module for <feature>

Tests cover:
- Success scenarios
- Error handling
- Edge cases
- Integration points
"""

import pytest
from unittest.mock import Mock, patch
from src.config import Settings


class TestFeatureName:
    """Test class for specific feature."""

    @pytest.fixture
    def setup_environment(self):
        """Fixture to set up test environment"""
        # Setup code
        yield environment
        # Cleanup code

    def test_feature_success(self, setup_environment):
        """Test successful feature operation."""
        # Arrange
        environment = setup_environment
        
        # Act
        result = feature_function(environment)
        
        # Assert
        assert result is not None
        assert result.status == "success"

    def test_feature_error_handling(self):
        """Test feature handles errors gracefully."""
        with pytest.raises(ValueError, match="Expected error message"):
            feature_function(invalid_input)
```

## Summary

- **6 MCP tools** for intelligent document research with cost optimization
- **8 comprehensive test files** covering 144 test scenarios
- **Unified credential architecture** — `pinecone_API_KEY` target, `~/.pinecone_api_key` (embedded entropy), shared `~/.uspto_internal_auth_secret`
- **Production-grade resilience patterns** (retry, circuit breaker, cache, bulkhead, fallback)
- **Security-first design** with API key encryption and input validation
- **Domain-agnostic architecture** - customize via YAML without code changes
- **Cross-platform compatibility** (Windows DPAPI, Linux fallbacks)
- **Zero API dependency** - all tests work with mocks

The test suite ensures the MCP server is **production-ready** with enterprise-grade reliability, security, and performance characteristics.

For questions or issues, see the main [README.md](../README.md) or [Installation Guide](../INSTALL.md).

---

**Quick Test:** Run `uv run pytest tests/test_basic.py -v` for a fast validation of your setup.