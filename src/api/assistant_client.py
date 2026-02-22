"""Pinecone Assistant API client using official SDK."""

import logging
from typing import Dict, Any, List, Optional, Union
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message as PineconeMessage
try:
    from ..config.config import Settings
    from ..models.models import Message, AssistantChatParams, AssistantContextParams, ContextSnippet, AssistantContextResponse, EvaluateAnswerParams
    from ..util.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        RateLimitError,
        ValidationError,
        TimeoutError,
        ServerError,
        SerializationError,
        CircuitBreakerError
    )
    from ..util.secure_logging import classify_api_error, log_error_safely, setup_secure_logging
    from ..util.error_context import ErrorContext, get_request_id
    from ..resilience.retry_utils import RetryExecutor
    from ..resilience.circuit_breaker import CircuitBreaker
    from ..resilience.cache import ResponseCache
    from ..resilience.bulkhead import Bulkhead
except ImportError:
    from config.config import Settings
    from models.models import Message, AssistantChatParams, AssistantContextParams, ContextSnippet, AssistantContextResponse, EvaluateAnswerParams
    from util.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        RateLimitError,
        ValidationError,
        TimeoutError,
        ServerError,
        SerializationError,
        CircuitBreakerError
    )
    from util.secure_logging import classify_api_error, log_error_safely, setup_secure_logging
    from util.error_context import ErrorContext, get_request_id
    from resilience.retry_utils import RetryExecutor
    from resilience.circuit_breaker import CircuitBreaker
    from resilience.cache import ResponseCache
    from resilience.bulkhead import Bulkhead


# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)


class PineconeAssistantClient:
    """Client for Pinecone Assistant API using official SDK."""

    # Error category to exception class mapping (class constant for testability)
    _EXCEPTION_MAP = {
        "authentication": AuthenticationError,
        "authorization": AuthorizationError,
        "rate_limit": RateLimitError,
        "validation": ValidationError,
        "timeout": TimeoutError,
        "server_error": ServerError,
    }

    def __init__(self, settings: Settings):
        """Initialize the client with settings."""
        self.settings = settings
        self.pc: Optional[Pinecone] = None
        self.assistant = None

        # RESILIENCE FIX: Initialize resilience patterns
        self._circuit_breaker = CircuitBreaker(
            name="pinecone_api",
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=Exception
        )
        self._retry_executor = RetryExecutor(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            retry_on=(RateLimitError, TimeoutError, ServerError, ConnectionError, OSError)
        )
        self._context_cache = ResponseCache(max_size=100, default_ttl=300)  # 5 minute TTL

        # RESILIENCE FIX: Bulkhead for concurrency limiting
        self._chat_bulkhead = Bulkhead(
            name="chat_api",
            max_concurrent=5,  # Max 5 concurrent chat requests
            max_wait_time=30.0
        )
        self._context_bulkhead = Bulkhead(
            name="context_api",
            max_concurrent=10,  # Max 10 concurrent context requests
            max_wait_time=30.0
        )

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def initialize(self):
        """Initialize the Pinecone client and assistant."""
        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=self.settings.pinecone_assistant_api_key)

            # Initialize the assistant
            self.assistant = self.pc.assistant.Assistant(
                assistant_name=self.settings.pinecone_assistant_name
            )

            logger.info(f"Initialized Pinecone Assistant client for '{self.settings.pinecone_assistant_name}'")

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone Assistant client: {e}")
            raise

    def close(self):
        """Close the client resources."""
        # The Pinecone SDK handles cleanup automatically
        self.pc = None
        self.assistant = None
        logger.info("Closed Pinecone Assistant client")

    def get_resilience_status(self) -> Dict[str, Any]:
        """Get current status of resilience patterns."""
        return {
            "circuit_breaker": self._circuit_breaker.get_status(),
            "cache_stats": {
                "size": len(self._context_cache._cache) if hasattr(self._context_cache, '_cache') else 0,
                "max_size": self._context_cache.max_size,
                "default_ttl": self._context_cache.default_ttl
            }
        }

    def _classify_and_transform_error(self, error: Exception) -> None:
        """Classify SDK error and raise appropriate custom exception.

        Args:
            error: The original SDK exception

        Raises:
            Appropriate custom exception based on error classification
        """
        from ..util.secure_logging import classify_api_error

        error_category, user_message = classify_api_error(error)

        # Handle not_found specially (includes assistant name)
        if error_category == "not_found":
            raise ResourceNotFoundError(
                f"Assistant '{self.settings.pinecone_assistant_name}' not found"
            )

        # Raise mapped exception or re-raise original
        exception_class = self._EXCEPTION_MAP.get(error_category)
        if exception_class:
            raise exception_class(user_message)
        else:
            raise  # Re-raise original exception

    def _convert_messages(self, messages: List[Message]) -> List[PineconeMessage]:
        """Convert our Message objects to Pinecone Message objects."""
        return [
            PineconeMessage(role=msg.role, content=msg.content) 
            for msg in messages
        ]
    
    def _convert_to_serializable(self, obj, default_model: str = None) -> Any:
        """Convert complex objects to JSON-serializable dictionaries."""
        if obj is None:
            return None
        
        # Handle Pydantic models with model_dump
        if hasattr(obj, 'model_dump'):
            try:
                return obj.model_dump()
            except (AttributeError, ValueError, TypeError) as e:
                logger.debug(f"Failed to call model_dump() on {type(obj)}: {e}")

        # Handle objects with dict() method
        if hasattr(obj, 'dict'):
            try:
                return obj.dict()
            except (AttributeError, ValueError, TypeError) as e:
                logger.debug(f"Failed to call dict() on {type(obj)}: {e}")
        
        # Handle lists
        if isinstance(obj, list):
            return [self._convert_to_serializable(item, default_model) for item in obj]
        
        # Handle dictionaries
        if isinstance(obj, dict):
            return {key: self._convert_to_serializable(value, default_model) for key, value in obj.items()}
        
        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Manual conversion for complex objects
        try:
            # Try to convert object attributes to dict
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):  # Skip private attributes
                        result[key] = self._convert_to_serializable(value, default_model)
                return result
            
            # Handle response object specifically
            if hasattr(obj, 'finish_reason'):
                result = {
                    "finish_reason": getattr(obj, 'finish_reason', None),
                    "message": self._convert_to_serializable(getattr(obj, 'message', None), default_model),
                    "id": getattr(obj, 'id', None),
                    "model": getattr(obj, 'model', default_model),
                    "usage": self._convert_to_serializable(getattr(obj, 'usage', None), default_model),
                    "citations": self._convert_to_serializable(getattr(obj, 'citations', []), default_model)
                }
                return result
            
            # Handle message objects
            if hasattr(obj, 'role') and hasattr(obj, 'content'):
                return {
                    "role": getattr(obj, 'role', None),
                    "content": getattr(obj, 'content', None)
                }
            
            # Handle usage objects
            if hasattr(obj, 'prompt_tokens') or hasattr(obj, 'total_tokens'):
                return {
                    "prompt_tokens": getattr(obj, 'prompt_tokens', None),
                    "completion_tokens": getattr(obj, 'completion_tokens', None),
                    "total_tokens": getattr(obj, 'total_tokens', None)
                }
            
            # Handle citation objects
            if hasattr(obj, 'position') and hasattr(obj, 'references'):
                return {
                    "position": getattr(obj, 'position', None),
                    "references": self._convert_to_serializable(getattr(obj, 'references', []), default_model)
                }
            
            # For unknown objects, try str conversion
            return str(obj)
            
        except Exception as e:
            logger.warning(f"Failed to convert object {type(obj)} to serializable: {e}")
            return str(obj)
    
    def chat(self, params: AssistantChatParams) -> Dict[str, Any]:
        """Send chat request to Pinecone Assistant with resilience."""
        request_id = get_request_id()

        with ErrorContext("chat", request_id=request_id, message_count=len(params.messages)):
            if not self.assistant:
                raise RuntimeError("Client not initialized. Call initialize() first.")

            if not params.messages:
                raise ValidationError("At least one message is required")

            # Validate model
            model = params.model or self.settings.pinecone_assistant_model
            if not self.settings.is_valid_model(model):
                logger.warning(f"[{request_id}] Model '{model}' may not be supported by Pinecone Assistant")

            # Convert messages to Pinecone format
            pinecone_messages = self._convert_messages(params.messages)

            # Build chat parameters
            chat_kwargs = {
                "messages": pinecone_messages,
                "model": model,
                "include_highlights": params.include_highlights,
                "stream": params.stream
            }

            # Add optional parameters
            if params.temperature is not None:
                chat_kwargs["temperature"] = params.temperature
            elif self.settings.default_temperature is not None:
                chat_kwargs["temperature"] = self.settings.default_temperature

            # Add 2025-10 API parameters
            if params.filter is not None:
                chat_kwargs["filter"] = params.filter
            if params.json_response:
                chat_kwargs["json_response"] = params.json_response
            if params.context_options is not None:
                chat_kwargs["context_options"] = params.context_options

            logger.info(f"[{request_id}] Sending chat request with {len(params.messages)} messages, model: {model}")

            def _make_chat_request():
                """Inner function for retry and circuit breaker wrapping."""
                try:
                    response = self.assistant.chat(**chat_kwargs)
                    result = self._convert_to_serializable(response, model)

                    # Log token usage if available
                    if "usage" in result and result["usage"] and self.settings.debug_logging:
                        usage = result["usage"]
                        total_tokens = usage.get('total_tokens', 'unknown') if isinstance(usage, dict) else getattr(usage, 'total_tokens', 'unknown')
                        logger.debug(f"[{request_id}] Token usage: {total_tokens} total")

                    return result

                except Exception as e:
                    # Classify and transform to custom exception for proper retry handling
                    self._classify_and_transform_error(e)

            try:
                # RESILIENCE: Use bulkhead → circuit breaker → retry logic
                return self._chat_bulkhead.execute(
                    lambda: self._circuit_breaker.call(
                        lambda: self._retry_executor.execute(_make_chat_request)
                    )
                )

            except CircuitBreakerError as e:
                log_error_safely(logger, f"[{request_id}] Circuit breaker open", e, include_traceback=False)
                raise ServerError(f"Service temporarily unavailable due to repeated failures. {e.message}")

            except (AuthenticationError, AuthorizationError, ResourceNotFoundError, ValidationError) as e:
                # Non-retriable errors - log and re-raise
                log_error_safely(logger, f"[{request_id}] Chat request", e, include_traceback=self.settings.debug_logging)
                raise

            except (RateLimitError, TimeoutError, ServerError) as e:
                # Retriable errors that exhausted retries
                log_error_safely(logger, f"[{request_id}] Chat request failed after retries", e, include_traceback=self.settings.debug_logging)
                raise

            except Exception as e:
                # Unexpected errors
                log_error_safely(logger, f"[{request_id}] Chat request", e, include_traceback=self.settings.debug_logging)
                raise RuntimeError(f"Request failed: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test connection to the Assistant API."""
        try:
            # Send a simple test message
            test_params = AssistantChatParams(
                messages=[Message(role="user", content="Test connection")],
                include_highlights=False
            )
            
            response = self.chat(test_params)
            
            # Check if we got a valid response
            if isinstance(response, dict) and "message" in response:
                message = response["message"]
                if isinstance(message, dict) and "content" in message and message["content"]:
                    logger.info("Connection test successful")
                    return True
                    
            logger.error("Connection test failed: Invalid response format")
            return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def context(self, params: AssistantContextParams) -> Dict[str, Any]:
        """Retrieve context snippets from Pinecone Assistant with resilience."""
        request_id = get_request_id()

        query_preview = (params.query or "")[:100]
        with ErrorContext("context", request_id=request_id, query=query_preview):
            if not self.assistant:
                raise RuntimeError("Client not initialized. Call initialize() first.")

            # Generate cache key
            cache_key = f"{params.query}:{params.messages}:{params.top_k}:{params.snippet_size}:{str(params.filter)}:{params.multimodal}:{params.include_binary_content}"

            # Check cache first
            cached_result = self._context_cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"[{request_id}] Cache hit for context query")
                return cached_result

            # Build context parameters — query and messages are mutually exclusive
            context_kwargs: Dict[str, Any] = {
                "top_k": params.top_k,
                "snippet_size": params.snippet_size
            }

            if params.messages:
                # Multi-turn context: convert dicts to PineconeMessage objects
                # Note: multimodal/include_binary_content are only valid with query input
                context_kwargs["messages"] = [
                    PineconeMessage(role=m["role"], content=m["content"])
                    for m in params.messages
                ]
            else:
                context_kwargs["query"] = params.query
                # multimodal/include_binary_content only supported with query input
                if params.multimodal is not None:
                    context_kwargs["multimodal"] = params.multimodal
                if params.include_binary_content is not None:
                    context_kwargs["include_binary_content"] = params.include_binary_content

            # filter is supported with both query and messages
            if params.filter:
                context_kwargs["filter"] = params.filter

            log_query = params.query[:50] if params.query else f"messages[{len(params.messages or [])}]"
            logger.info(f"[{request_id}] Retrieving context for: '{log_query}' (top_k={params.top_k}, snippet_size={params.snippet_size})")

            def _make_context_request():
                """Inner function for retry and circuit breaker wrapping."""
                try:
                    response = self.assistant.context(**context_kwargs)
                    result = self._convert_to_serializable(response)

                    # Log snippet count if available
                    if "snippets" in result and self.settings.debug_logging:
                        snippet_count = len(result["snippets"]) if isinstance(result["snippets"], list) else 0
                        logger.debug(f"[{request_id}] Retrieved {snippet_count} context snippets")

                    return result

                except Exception as e:
                    # Classify and transform to custom exception
                    self._classify_and_transform_error(e)

            try:
                # RESILIENCE: Use bulkhead → circuit breaker → retry logic
                result = self._context_bulkhead.execute(
                    lambda: self._circuit_breaker.call(
                        lambda: self._retry_executor.execute(_make_context_request)
                    )
                )

                # Cache successful result
                self._context_cache.set(cache_key, result)
                logger.debug(f"[{request_id}] Cached context result")

                return result

            except CircuitBreakerError as e:
                log_error_safely(logger, f"[{request_id}] Circuit breaker open", e, include_traceback=False)
                raise ServerError(f"Service temporarily unavailable due to repeated failures. {e.message}")

            except (AuthenticationError, AuthorizationError, ResourceNotFoundError, ValidationError) as e:
                # Non-retriable errors - log and re-raise
                log_error_safely(logger, f"[{request_id}] Context request", e, include_traceback=self.settings.debug_logging)
                raise

            except (RateLimitError, TimeoutError, ServerError) as e:
                # Retriable errors that exhausted retries
                log_error_safely(logger, f"[{request_id}] Context request failed after retries", e, include_traceback=self.settings.debug_logging)
                raise

            except Exception as e:
                # Unexpected errors
                log_error_safely(logger, f"[{request_id}] Context request", e, include_traceback=self.settings.debug_logging)
                raise RuntimeError(f"Request failed: {str(e)}")

    def evaluate(self, params: EvaluateAnswerParams) -> Dict[str, Any]:
        """Evaluate an answer against a ground truth using the alignment metrics endpoint."""
        request_id = get_request_id()

        with ErrorContext("evaluate", request_id=request_id):
            try:
                from pinecone_plugins.assistant.evaluation.core.client import ApiClient
                from pinecone_plugins.assistant.evaluation.core.client.configuration import Configuration
                from pinecone_plugins.assistant.evaluation.core.client.api.metrics_api import MetricsApi
                from pinecone_plugins.assistant.evaluation.core.client.model.alignment_request import AlignmentRequest
            except ImportError as e:
                raise RuntimeError(f"Evaluation SDK not available: {e}") from e

            config = Configuration()
            # Evaluation SDK expects host ending in /assistant
            host = self.settings.pinecone_assistant_host.rstrip('/')
            if not host.endswith('/assistant'):
                host = f"{host}/assistant"
            config.host = host
            config.api_key = {"ApiKeyAuth": self.settings.pinecone_assistant_api_key}

            try:
                client = ApiClient(configuration=config)
                api = MetricsApi(api_client=client)
                request = AlignmentRequest(
                    question=params.question,
                    answer=params.answer,
                    ground_truth_answer=params.ground_truth_answer
                )
                response = api.metrics_alignment(request)

                # Convert to serializable dict
                result = self._convert_to_serializable(response)
                logger.info(f"[{request_id}] Evaluation complete")
                return result

            except Exception as e:
                error_str = str(e)
                # Surface free-tier restriction as a clear user-facing error
                if "free tier" in error_str.lower() or "Endpoint not supported for free tier" in error_str:
                    raise ValueError(
                        "evaluate_answer requires a Pinecone Standard (paid) plan. "
                        "The evaluation endpoint is not available on the free tier. "
                        "Upgrade at https://app.pinecone.io to use this feature."
                    ) from e
                log_error_safely(logger, f"[{request_id}] Evaluation request", e, include_traceback=self.settings.debug_logging)
                raise RuntimeError(f"Evaluation request failed: {str(e)}") from e

    def get_assistant_info(self) -> Dict[str, Any]:
        """Get information about the assistant configuration."""
        return {
            "name": self.settings.pinecone_assistant_name,
            "host": self.settings.pinecone_assistant_host,
            "default_model": self.settings.pinecone_assistant_model,
            "api_version": "2025-10",
            "sdk_version": "pinecone-plugin-assistant"
        }


class AssistantClientManager:
    """Manager for Assistant client instances with connection pooling."""
    
    _instance: Optional[PineconeAssistantClient] = None
    _settings: Optional[Settings] = None
    
    @classmethod
    def get_client(cls, settings: Settings) -> PineconeAssistantClient:
        """Get or create a client instance."""
        if cls._instance is None or cls._settings != settings:
            if cls._instance:
                cls._instance.close()
                
            cls._instance = PineconeAssistantClient(settings)
            cls._instance.initialize()
            cls._settings = settings
            
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close the managed client."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            cls._settings = None

    @classmethod
    def update_configuration(cls, assistant_name: Optional[str] = None,
                           assistant_host: Optional[str] = None,
                           model: Optional[str] = None) -> Dict[str, Any]:
        """
        Update assistant configuration mid-session.

        Args:
            assistant_name: New assistant name (optional)
            assistant_host: New assistant host URL (optional, auto-detected if omitted)
            model: New default model (optional)

        Returns:
            Dictionary with update status and changes made
        """
        if not cls._settings:
            raise RuntimeError("No configuration to update. Initialize client first.")

        changes = {}
        old_config = {
            "assistant_name": cls._settings.pinecone_assistant_name,
            "assistant_host": cls._settings.pinecone_assistant_host,
            "model": cls._settings.pinecone_assistant_model
        }

        # Update assistant name and potentially host
        if assistant_name:
            # If assistant name changes, we need to detect the new host
            if assistant_name != cls._settings.pinecone_assistant_name:
                from pinecone import Pinecone

                # Close existing client
                if cls._instance:
                    cls._instance.close()

                # Detect host for new assistant
                if not assistant_host:
                    try:
                        pc = Pinecone(api_key=cls._settings.pinecone_assistant_api_key)
                        assistant_info = pc.assistant.describe_assistant(assistant_name=assistant_name)

                        # Handle both dict and object responses
                        if hasattr(assistant_info, 'host'):
                            assistant_host = assistant_info.host
                        else:
                            assistant_host = assistant_info.get('host')
                    except Exception as e:
                        raise RuntimeError(f"Failed to auto-detect host for assistant '{assistant_name}': {e}")

                # Update settings
                cls._settings.pinecone_assistant_name = assistant_name
                cls._settings.pinecone_assistant_host = assistant_host

                changes["assistant_name"] = {"old": old_config["assistant_name"], "new": assistant_name}
                changes["assistant_host"] = {"old": old_config["assistant_host"], "new": assistant_host}

                # Recreate client with new settings
                cls._instance = PineconeAssistantClient(cls._settings)
                cls._instance.initialize()

        # Update host if explicitly provided
        elif assistant_host and assistant_host != cls._settings.pinecone_assistant_host:
            cls._settings.pinecone_assistant_host = assistant_host
            changes["assistant_host"] = {"old": old_config["assistant_host"], "new": assistant_host}

            # Recreate client
            if cls._instance:
                cls._instance.close()
            cls._instance = PineconeAssistantClient(cls._settings)
            cls._instance.initialize()

        # Update model (doesn't require client recreation)
        if model and model != cls._settings.pinecone_assistant_model:
            if cls._settings.is_valid_model(model):
                cls._settings.pinecone_assistant_model = model
                changes["model"] = {"old": old_config["model"], "new": model}
            else:
                raise ValueError(f"Invalid model: {model}")

        return {
            "status": "success" if changes else "no_changes",
            "changes": changes,
            "current_config": {
                "assistant_name": cls._settings.pinecone_assistant_name,
                "assistant_host": cls._settings.pinecone_assistant_host,
                "model": cls._settings.pinecone_assistant_model
            }
        }