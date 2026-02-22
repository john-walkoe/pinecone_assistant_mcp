"""Main MCP server for USPTO Pinecone Assistant."""

import logging
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Prompt, GetPromptResult

try:
    # Try relative imports first (when imported as module)
    from .prompts import PROMPTS, get_prompt_result
    from .config.config import get_settings
    from .config.secure_storage import get_secure_api_key
    from .api.assistant_client import AssistantClientManager
    from .services.strategic_search import StrategySearchProcessor
    from .services.strategic_context import StrategicContextSearcher
    from .models.models import AssistantChatParams, StrategySearchParams, Message, AssistantContextParams, StrategyContextParams, EvaluateAnswerParams
    from .util.secure_logging import setup_secure_logging
    from .util.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        RateLimitError,
        ValidationError,
        TimeoutError,
        ServerError,
        CircuitBreakerError,
        ConfigurationError
    )
    from .util.error_context import RequestScope, format_error_response, get_request_id
    from .util.security_audit import security_audit
    from .util.rate_limiter import RateLimiter
except ImportError:
    # Fallback to absolute imports (when run as script)
    from prompts import PROMPTS, get_prompt_result
    from config.config import get_settings
    from config.secure_storage import get_secure_api_key
    from api.assistant_client import AssistantClientManager
    from services.strategic_search import StrategySearchProcessor
    from services.strategic_context import StrategicContextSearcher
    from models.models import AssistantChatParams, StrategySearchParams, Message, AssistantContextParams, StrategyContextParams, EvaluateAnswerParams
    from util.secure_logging import setup_secure_logging
    from util.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        RateLimitError,
        ValidationError,
        TimeoutError,
        ServerError,
        CircuitBreakerError,
        ConfigurationError
    )
    from util.error_context import RequestScope, format_error_response, get_request_id
    from util.security_audit import security_audit
    from util.rate_limiter import RateLimiter


# SECURITY FIX (L-1): Configure secure logging with auto-redaction
logger = setup_secure_logging(
    logger_name=__name__,
    level=logging.INFO,
    log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    enable_file_logging=False  # Use stdout for MCP servers
)

# RESILIENCE FIX: Initialize rate limiters per tool (different costs per operation)
_rate_limiters = {
    "assistant_chat": RateLimiter(max_requests=50, window_seconds=60, name="chat"),
    "assistant_context": RateLimiter(max_requests=100, window_seconds=60, name="context"),
    "assistant_strategic_multi_search_chat": RateLimiter(max_requests=10, window_seconds=60, name="strategic_search"),
    "assistant_strategic_multi_search_context": RateLimiter(max_requests=20, window_seconds=60, name="strategic_context"),
    "evaluate_answer": RateLimiter(max_requests=20, window_seconds=60, name="evaluate"),
}

# Server instructions for Claude Code tool search (MCPSearch auto-discovery)
# assistant_context and get_configuration_status are always immediately useful;
# the remaining tools are discovered on-demand when needed.
SERVER_INSTRUCTIONS = """
Pinecone Assistant MCP provides document knowledge base research through 7 tools.

ALWAYS-AVAILABLE TOOLS (load these first — cheapest and most common):
1. assistant_context - Raw document retrieval (context tokens only, ~5-10K/query). Use for almost all lookups.
2. get_configuration_status - Check current assistant name and model (free).

PROGRESSIVE WORKFLOW:
1. Quick lookup: Use assistant_context(query="...", top_k=3-5)
2. Multi-angle research: Search for assistant_strategic_multi_search_context
3. AI synthesis: Search for assistant_strategic_multi_search_chat or assistant_chat
4. Switch knowledge base: Search for update_configuration
5. Evaluate answer quality: Search for evaluate_answer (requires paid Pinecone plan)

TOKEN BUDGET (Free tier — LIFETIME, do NOT reset monthly):
- Context tokens: 500K lifetime (used by assistant_context and *_context tools)
- Input tokens: 1.5M lifetime (used by assistant_chat and *_chat tools)
- Output tokens: 200K lifetime

TOOL SELECTION RULE: Always start with assistant_context. Only escalate to chat tools when AI synthesis is explicitly needed.
"""

# Initialize server
server = Server("pinecone-assistant", instructions=SERVER_INSTRUCTIONS)

# Global instances
_settings = None
_client = None
_search_processor = None
_context_searcher = None


async def initialize():
    """Initialize server components."""
    global _settings, _client, _search_processor, _context_searcher
    
    try:
        # Load settings
        _settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Initialize client
        _client = AssistantClientManager.get_client(_settings)
        logger.info("Pinecone Assistant client initialized")
        
        # Test connection
        if _client.test_connection():
            logger.info("Assistant connection test successful")
        else:
            logger.warning("Assistant connection test failed - check configuration")
        
        # Initialize strategic search processor
        _search_processor = StrategySearchProcessor()
        logger.info(f"Strategic search processor loaded with {len(_search_processor.get_available_domains())} domains")
        
        # Initialize strategic context searcher
        _context_searcher = StrategicContextSearcher(_client)
        logger.info("Strategic context searcher initialized")
        
        logger.info("USPTO Pinecone Assistant MCP server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for USPTO Pinecone Assistant."""
    
    # Generate dynamic domain descriptions from loaded YAML
    available_domains = _search_processor.get_available_domains()
    domain_descriptions = []

    for domain in available_domains:
        searches = _search_processor.patterns[domain].searches
        enabled_searches = [s for s in searches if s.enabled]

        # Simple description with just domain name and search count
        if enabled_searches:
            description = f"**{domain}**: {len(enabled_searches)} search patterns"
        else:
            description = f"**{domain}**: (no enabled searches)"

        domain_descriptions.append(description)

    dynamic_domain_list = '\n            - '.join([''] + domain_descriptions)
    
    return [
        Tool(
            name="assistant_context",
            description="""
            ⭐ START HERE - Retrieve raw document chunks without AI processing.

            **Token Cost**: Uses context tokens (Free tier: 500K lifetime, does NOT reset monthly). ~5-10K per query.

            **Returns**: Raw document snippets with relevancy scores and source references.
            No AI synthesis - perfect for custom analysis in your host LLM.

            **Best for**: Most queries. Try this first before AI-powered tools.

            **Parameters**:
            - query: What to search for (required unless messages provided)
            - top_k: Number of chunks (1-64, default: 5)
            - snippet_size: Tokens per chunk (512-8192, default: 2048)
            - filter: Optional metadata filtering
            - multimodal: Retrieve image context from PDFs (API default: true, query-only)
            - include_binary_content: Include base64 image data (API default: true, query-only, set false to reduce size)
            - messages: Multi-turn messages as alternative to query (multimodal params ignored when using messages)

            **Example**:
            assistant_context(
              query: "Section 101 eligibility standards",
              top_k: 5,
              snippet_size: 2048
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval (required unless messages provided)"
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 64,
                        "default": 5,
                        "description": "Number of context snippets to retrieve"
                    },
                    "snippet_size": {
                        "type": "integer",
                        "minimum": 512,
                        "maximum": 8192,
                        "default": 2048,
                        "description": "Maximum tokens per snippet"
                    },
                    "filter": {
                        "type": "object",
                        "description": "Optional metadata filter for document selection"
                    },
                    "multimodal": {
                        "type": "boolean",
                        "description": "Enable multimodal context retrieval (images from PDFs). API default: true."
                    },
                    "include_binary_content": {
                        "type": "boolean",
                        "description": "Include base64 image data in response. Set false to reduce response size. API default: true."
                    },
                    "messages": {
                        "type": "array",
                        "description": "Multi-turn messages as alternative to query. Use for conversation-aware context retrieval.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        }
                    }
                }
            }
        ),

        Tool(
            name="assistant_strategic_multi_search_context",
            description=f"""
            Execute multiple strategic searches returning raw document chunks (no AI synthesis).

            **Token Cost**: Uses context tokens (Free tier: 500K lifetime, does NOT reset monthly). ~10-15K per query.

            **Available domains**:{dynamic_domain_list}

            **How it works**: Applies domain-specific search patterns from strategic-searches.yaml,
            executes multiple context retrievals, returns aggregated raw chunks.

            **Best for**: Comprehensive multi-topic document retrieval without AI synthesis.

            **Parameters**:
            - query: Primary research question or topic
            - domain: Search domain from strategic-searches.yaml
            - top_k: Number of chunks per search (1-64, default: 5)
            - snippet_size: Tokens per chunk (512-8192, default: 2048)
            - max_searches: Limit searches executed (default: all enabled)

            **Example**:
            assistant_strategic_multi_search_context(
              query: "Section 101 eligibility standards",
              domain: "section_101_eligibility",
              max_searches: 2
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Primary research question or topic"
                    },
                    "domain": {
                        "type": "string",
                        "default": "core_examination_framework",
                        "description": "Search domain for pattern selection"
                    },
                    "max_searches": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Limit number of pattern searches"
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 64,
                        "default": 5,
                        "description": "Number of snippets per search pattern"
                    },
                    "snippet_size": {
                        "type": "integer",
                        "minimum": 512,
                        "maximum": 8192,
                        "default": 2048,
                        "description": "Maximum tokens per snippet"
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="assistant_strategic_multi_search_chat",
            description=f"""
            ⚠️ Higher token cost - uses input tokens. Try assistant_strategic_multi_search_context first.

            Execute multiple strategic searches with AI-synthesized responses.

            **Token Cost**: Input + output tokens (Free tier: 1.5M input + 200K output lifetime, does NOT reset monthly).
            ~30K input + ~5K output per query.

            **Available domains**:{dynamic_domain_list}

            **How it works**: Applies search patterns from strategic-searches.yaml, executes
            multiple AI chat searches, returns AI-synthesized results with citations.

            **Best for**: When you need AI to synthesize information across multiple searches.

            **Parameters**:
            - query: Primary research question
            - domain: Search domain from strategic-searches.yaml
            - max_searches: Limit searches executed (default: all enabled)
            - model: AI model (default: gpt-4o)
              Options: gpt-4o, gpt-4.1, o4-mini, claude-3-5-sonnet, claude-3-7-sonnet, claude-sonnet-4-5, gemini-2.5-pro

            **Example**:
            assistant_strategic_multi_search_chat(
              query: "Section 101 eligibility for AI inventions",
              domain: "section_101_eligibility",
              max_searches: 2
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Primary research question or topic"
                    },
                    "domain": {
                        "type": "string",
                        "default": "core_examination_framework",
                        "description": "Search domain for pattern selection - see USAGE_EXAMPLES.md for guidance"
                    },
                    "max_searches": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Limit number of pattern searches (default: all enabled)"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["gpt-4o", "gpt-4.1", "gpt-5", "o4-mini", "claude-sonnet-4-5", "gemini-2.5-pro"],
                        "default": "gpt-4o",
                        "description": "AI model for response generation"
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="assistant_chat",
            description="""
            ⚠️ High token cost - Use only when AI analysis needed. Try assistant_context first.

            Direct conversation with Pinecone Assistant for AI-powered research.

            **Token Cost**: Input + output tokens (Free tier: 1.5M input + 200K output lifetime, does NOT reset monthly).
            ~30K input + ~2-5K output per query.

            **Features**: Multi-turn conversations, rich citations with highlights, model selection.

            **Best for**: Complex analysis requiring AI synthesis (not simple lookups).

            **⚠️ Multi-turn Conversation Warning**:
            The API is stateless. Only include history when new question explicitly references
            prior context (pronouns like "that", references like "as mentioned").

            **Include history ONLY if**: Question contains "that", "this", "as mentioned", etc.
            **Default**: Send single-message queries (stateless).

            **Token Impact**:
            - Stateless: ~30K input per query
            - With history (4 turns): ~130K total (4x cost!)
            - Smart approach: Use stateless queries when possible

            **Parameters**:
            - messages: Conversation messages (keep minimal!)
            - model: AI model (default: gpt-4o)
              Options: gpt-4o, gpt-4.1, gpt-5, o4-mini, claude-sonnet-4-5, gemini-2.5-pro
            - temperature: Randomness (0.0=focused, 2.0=creative)
            - include_highlights: Include citations (default: true)
            - stream: Enable streaming (default: false)
            - filter: Document metadata filter to scope chat to specific documents
            - json_response: Request structured JSON output (default: false)
            - context_options: Limit context sent to LLM to reduce token usage.
              Fields: top_k (default: 16) and snippet_size (default: 2048).
              Example: {"top_k": 5, "snippet_size": 1024} cuts ~75% of prompt tokens.

            **Example**:
            assistant_chat(
              messages: [{
                role: "user",
                content: "Section 101 eligibility for AI inventions"
              }],
              include_highlights: true
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant"],
                                    "description": "Message role"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Message content"
                                }
                            },
                            "required": ["role", "content"]
                        },
                        "description": "Conversation messages - keep minimal! Only include history if new question references prior context."
                    },
                    "model": {
                        "type": "string",
                        "enum": ["gpt-4o", "gpt-4.1", "gpt-5", "o4-mini", "claude-sonnet-4-5", "gemini-2.5-pro"],
                        "default": "gpt-4o",
                        "description": "AI model for response generation"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 2.0,
                        "description": "Response randomness (0.0=focused, 2.0=creative)"
                    },
                    "include_highlights": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include citation highlights (recommended)"
                    },
                    "stream": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable streaming responses"
                    },
                    "filter": {
                        "type": "object",
                        "description": "Document metadata filter to scope chat to specific documents"
                    },
                    "json_response": {
                        "type": "boolean",
                        "default": False,
                        "description": "Request structured JSON output from the assistant"
                    },
                    "context_options": {
                        "type": "object",
                        "description": "Limit context sent to LLM to reduce prompt token usage. API default: top_k=16, snippet_size=2048.",
                        "properties": {
                            "top_k": {
                                "type": "integer",
                                "description": "Max context snippets sent to LLM (default: 16). Lower = fewer tokens."
                            },
                            "snippet_size": {
                                "type": "integer",
                                "description": "Max tokens per snippet (default: 2048). Lower = fewer tokens."
                            }
                        }
                    }
                },
                "required": ["messages"]
            }
        ),

        Tool(
            name="get_configuration_status",
            description="""
            Check current assistant configuration.

            **Returns**: Assistant name, host, and model.

            No parameters required.
            """,
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        Tool(
            name="update_configuration",
            description="""
            Switch between different Pinecone Assistants or change settings mid-conversation.

            **Use Cases**: Switch knowledge bases (Free tier: up to 5 assistants), change default model.

            **Parameters**:
            - assistant_name: Assistant to switch to (required)
            - assistant_host: Host URL (optional, auto-detected)
            - model: Default AI model (optional)

            **Notes**: Changes persist for current session only. Restart Claude to revert.

            **Example**:
            update_configuration(
              assistant_name: "case-law-assistant",
              model: "claude-sonnet-4-5"
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "assistant_name": {
                        "type": "string",
                        "description": "Name of the Pinecone Assistant to switch to"
                    },
                    "assistant_host": {
                        "type": "string",
                        "description": "Host URL for the assistant (optional, will auto-detect if not provided)"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["gpt-4o", "gpt-4.1", "gpt-5", "o4-mini", "claude-sonnet-4-5", "gemini-2.5-pro"],
                        "description": "Default AI model to use"
                    }
                },
                "required": ["assistant_name"]
            }
        ),

        Tool(
            name="evaluate_answer",
            description="""
            Evaluate the quality of an AI-generated answer against a ground truth answer.

            **⚠️ Requires Pinecone Standard (paid) plan.** Returns an error on free tier.

            **Token Cost**: Uses Pinecone's evaluation LLM. ~5-10K tokens per call.

            **Returns**: Three quality scores (0.0–1.0) plus per-fact entailment reasoning.

            **Scores**:
            - correctness: Precision — what fraction of answer facts are supported by ground truth
            - completeness: Recall — what fraction of ground truth facts appear in the answer
            - alignment: Harmonic mean of correctness and completeness (overall quality)

            **Best for**:
            - Benchmarking assistant responses against known-correct answers
            - Validating that retrieved context yields accurate answers
            - Regression testing after prompt or document changes

            **Parameters**:
            - question: The question that was asked
            - answer: The AI-generated answer to evaluate
            - ground_truth_answer: The correct/expected answer to compare against

            **Example**:
            evaluate_answer(
              question: "What is the Alice two-step test?",
              answer: "The Alice test has two steps: step 1 determines...",
              ground_truth_answer: "Alice Corp v. CLS Bank established a two-part test..."
            )
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question that was asked"
                    },
                    "answer": {
                        "type": "string",
                        "description": "The AI-generated answer to evaluate"
                    },
                    "ground_truth_answer": {
                        "type": "string",
                        "description": "The correct/expected answer to compare against"
                    }
                },
                "required": ["question", "answer", "ground_truth_answer"]
            }
        )
    ]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompt templates."""
    return PROMPTS


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Return a specific prompt with resolved argument substitutions."""
    try:
        return get_prompt_result(name, arguments)
    except ValueError as e:
        logger.warning(f"Unknown prompt requested: {name}")
        raise


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls with specific exception handling."""
    # RESILIENCE FIX: Create request scope for error correlation
    with RequestScope() as scope:
        request_id = scope.request_id

        # RESILIENCE FIX: Check per-tool rate limit before processing
        limiter = _rate_limiters.get(name)
        if limiter:
            allowed, retry_after = limiter.check_rate("default")
        else:
            allowed, retry_after = True, None  # No rate limit for unconfigured tools

        if not allowed:
            logger.warning(f"[{request_id}] Rate limit exceeded for tool {name}")
            security_audit.log_rate_limit(name, retry_after, request_id)

            error_response = {
                "error": True,
                "code": "RATE_LIMIT",
                "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                "retry_after": retry_after,
                "request_id": request_id,
                "recoverable": True
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

        try:
            if name == "assistant_chat":
                return await handle_assistant_chat(arguments)
            elif name == "assistant_strategic_multi_search_chat":
                return await handle_strategic_search(arguments)
            elif name == "assistant_context":
                return await handle_assistant_context(arguments)
            elif name == "assistant_strategic_multi_search_context":
                return await handle_strategic_context_search(arguments)
            elif name == "get_configuration_status":
                return await handle_get_configuration_status(arguments)
            elif name == "update_configuration":
                return await handle_update_configuration(arguments)
            elif name == "evaluate_answer":
                return await handle_evaluate_answer(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        # RESILIENCE FIX: Specific exception handlers with structured responses
        except ValidationError as e:
            logger.warning(f"[{request_id}] Validation error in {name}: {e.message}")
            security_audit.log_validation_failure(name, e.message, request_id)
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except AuthenticationError as e:
            logger.error(f"[{request_id}] Authentication failed for {name}")
            security_audit.log_auth_failure(
                assistant_name=_settings.pinecone_assistant_name if _settings else "unknown",
                failure_reason="authentication_error",
                request_id=request_id,
            )
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except AuthorizationError as e:
            logger.error(f"[{request_id}] Authorization denied for {name}")
            security_audit.log_authorization_failure(
                assistant_name=_settings.pinecone_assistant_name if _settings else "unknown",
                request_id=request_id,
            )
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except ResourceNotFoundError as e:
            logger.error(f"[{request_id}] Resource not found in {name}: {e.message}")
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except RateLimitError as e:
            logger.warning(f"[{request_id}] Rate limit exceeded for {name}")
            security_audit.log_rate_limit(name, request_id)
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except TimeoutError as e:
            logger.error(f"[{request_id}] Timeout in {name}: {e.message}")
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except ServerError as e:
            logger.error(f"[{request_id}] Server error in {name}: {e.message}")
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except CircuitBreakerError as e:
            logger.error(f"[{request_id}] Circuit breaker open for {name}")
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except ConfigurationError as e:
            logger.error(f"[{request_id}] Configuration error in {name}: {e.message}")
            error_response = format_error_response(e)
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except ValueError as e:
            # Handle ValueError (like unknown tool) as validation error
            logger.warning(f"[{request_id}] Invalid input for {name}: {e}")
            error_response = {
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "recoverable": False,
                "request_id": request_id
            }
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]

        except Exception as e:
            # Fallback for unexpected errors - don't expose internal details
            logger.error(f"[{request_id}] Unexpected error in {name}: {e}", exc_info=True)
            error_response = {
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"An internal error occurred. Reference ID: {request_id}",
                "recoverable": False,
                "request_id": request_id
            }
            return [TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )]


async def handle_assistant_chat(args: dict) -> list[TextContent]:
    """Handle direct chat with the Assistant."""
    try:
        # Validate and parse arguments
        messages_data = args.get("messages", [])
        if not messages_data:
            raise ValueError("At least one message is required")

        # Convert message dictionaries to Message objects
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]

        # Create chat parameters
        params = AssistantChatParams(
            messages=messages,
            model=args.get("model", "gpt-4o"),
            temperature=args.get("temperature"),
            include_highlights=args.get("include_highlights", True),
            stream=args.get("stream", False),
            filter=args.get("filter"),
            json_response=args.get("json_response", False),
            context_options=args.get("context_options")
        )

        logger.info(f"Processing chat request with {len(messages)} messages")

        # Execute chat
        response = _client.chat(params)

        # Format clean response: answer + condensed sources + token summary
        output_lines = []

        # 1. Main answer content
        message = response.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else str(message)
        if content:
            output_lines.append(content)

        # 2. Condensed citations — unique filenames + one 150-char highlight per file
        citations = response.get("citations", [])
        if citations:
            output_lines.append("\n---\n**Sources:**")
            seen_files: dict = {}
            for citation in citations:
                refs = citation.get("references", []) if isinstance(citation, dict) else []
                for ref in refs:
                    file_info = ref.get("file", {}) if isinstance(ref, dict) else {}
                    file_name = file_info.get("name", "Unknown") if isinstance(file_info, dict) else "Unknown"
                    if file_name in seen_files:
                        continue
                    highlight = ref.get("highlight", {}) if isinstance(ref, dict) else {}
                    excerpt = highlight.get("content", "").strip() if isinstance(highlight, dict) else ""
                    if len(excerpt) > 150:
                        excerpt = excerpt[:150].rstrip() + "..."
                    seen_files[file_name] = excerpt
            for file_name, excerpt in seen_files.items():
                if excerpt:
                    output_lines.append(f'- **{file_name}**: "{excerpt}"')
                else:
                    output_lines.append(f"- **{file_name}**")

        # 3. Token usage summary
        usage = response.get("usage", {})
        if usage and isinstance(usage, dict):
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", 0)
            if total:
                output_lines.append(
                    f"\n*Tokens: {prompt:,} prompt + {completion:,} completion = {total:,} total*"
                )

        return [TextContent(
            type="text",
            text="\n".join(output_lines)
        )]

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise


async def handle_strategic_search(args: dict) -> list[TextContent]:
    """Handle strategic multi-search."""
    try:
        # Validate domain against available domains
        domain = args.get("domain", "core_examination_framework")
        available_domains = _search_processor.get_available_domains()
        
        if domain not in available_domains:
            available_list = ', '.join(available_domains)
            raise ValueError(
                f"Unknown search domain: '{domain}'. Available domains: {available_list}"
            )
        
        # Create search parameters
        params = StrategySearchParams(
            query=args["query"],
            domain=domain,
            max_searches=args.get("max_searches"),
            model=args.get("model", "gpt-4o")
        )
        
        logger.info(f"Processing strategic search for domain '{params.domain}': {params.query}")
        
        # Execute strategic search
        result = _search_processor.execute_strategic_search(_client, params)
        
        # Format response
        return [TextContent(
            type="text", 
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Strategic search failed: {e}")
        raise


async def handle_assistant_context(args: dict) -> list[TextContent]:
    """Handle context retrieval from the Assistant."""
    try:
        # Create context parameters
        params = AssistantContextParams(
            query=args.get("query"),
            top_k=args.get("top_k", 5),
            snippet_size=args.get("snippet_size", 2048),
            filter=args.get("filter"),
            multimodal=args.get("multimodal"),
            include_binary_content=args.get("include_binary_content"),
            messages=args.get("messages")
        )
        
        logger.info(f"Processing context request: '{params.query}' (top_k={params.top_k}, snippet_size={params.snippet_size})")
        
        # Execute context retrieval
        response = _client.context(params)
        
        # Format response
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Context request failed: {e}")
        raise


async def handle_strategic_context_search(args: dict) -> list[TextContent]:
    """Handle strategic multi-search context retrieval."""
    try:
        # Validate domain against available domains
        domain = args.get("domain", "core_examination_framework")
        available_domains = _search_processor.get_available_domains()

        if domain not in available_domains:
            available_list = ', '.join(available_domains)
            raise ValueError(
                f"Unknown search domain: '{domain}'. Available domains: {available_list}"
            )

        # Create context search parameters
        params = StrategyContextParams(
            query=args["query"],
            domain=domain,
            max_searches=args.get("max_searches"),
            top_k=args.get("top_k", 5),
            snippet_size=args.get("snippet_size", 2048)
        )
        
        logger.info(f"Processing strategic context search for domain '{params.domain}': {params.query}")
        
        # Execute strategic context search
        result = _context_searcher.execute_strategic_context_search(params)
        
        # Format response
        return [TextContent(
            type="text", 
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Strategic context search failed: {e}")
        raise


async def handle_get_configuration_status(args: dict) -> list[TextContent]:
    """Handle configuration status request."""
    try:
        # Get current configuration from the client
        config_info = _client.get_assistant_info()

        # Format minimal response
        response = (
            f"**Current Configuration:**\n"
            f"• Assistant: {config_info['name']}\n"
            f"• Host: {config_info['host']}\n"
            f"• Model: {config_info['default_model']}"
        )

        return [TextContent(
            type="text",
            text=response
        )]

    except Exception as e:
        logger.error(f"Configuration status request failed: {e}")
        raise


async def handle_update_configuration(args: dict) -> list[TextContent]:
    """Handle configuration updates for switching assistants or changing settings."""
    global _client, _context_searcher

    try:
        assistant_name = args.get("assistant_name")
        assistant_host = args.get("assistant_host")
        model = args.get("model")

        logger.info(f"Updating configuration: assistant_name={assistant_name}, assistant_host={assistant_host}, model={model}")

        # Update configuration via AssistantClientManager
        result = AssistantClientManager.update_configuration(
            assistant_name=assistant_name,
            assistant_host=assistant_host,
            model=model
        )

        # SECURITY FIX (L-4): Log configuration changes to security audit
        if result["status"] == "success" and result.get("changes"):
            security_audit.log_config_change(
                changes=result["changes"],
                request_id=get_request_id(),
            )

        # CRITICAL: Update global client reference if configuration changed
        # This ensures all subsequent tool calls use the new client
        if result["status"] == "success" and result["changes"]:
            # Get the updated client from the manager
            _client = AssistantClientManager.get_client(AssistantClientManager._settings)

            # Reinitialize context searcher with new client
            _context_searcher = StrategicContextSearcher(_client)

            logger.info("Global client and context searcher updated with new configuration")

        # Format response
        response_lines = []

        if result["status"] == "success":
            response_lines.append("✅ Configuration updated successfully!")
            response_lines.append("")

            if result["changes"]:
                response_lines.append("**Changes Made:**")
                for key, change in result["changes"].items():
                    response_lines.append(f"  • {key}:")
                    response_lines.append(f"      Old: {change['old']}")
                    response_lines.append(f"      New: {change['new']}")
                response_lines.append("")

            response_lines.append("**Current Configuration:**")
            response_lines.append(f"  • Assistant: {result['current_config']['assistant_name']}")
            response_lines.append(f"  • Host: {result['current_config']['assistant_host']}")
            response_lines.append(f"  • Model: {result['current_config']['model']}")
            response_lines.append("")
            response_lines.append("All subsequent tool calls will use this new configuration.")
            response_lines.append("Restart Claude Desktop to revert to original environment configuration.")

        else:
            response_lines.append("ℹ️ No changes made - configuration already matches requested values.")
            response_lines.append("")
            response_lines.append("**Current Configuration:**")
            response_lines.append(f"  • Assistant: {result['current_config']['assistant_name']}")
            response_lines.append(f"  • Host: {result['current_config']['assistant_host']}")
            response_lines.append(f"  • Model: {result['current_config']['model']}")

        return [TextContent(
            type="text",
            text="\n".join(response_lines)
        )]

    except Exception as e:
        logger.error(f"Configuration update failed: {e}")
        raise


async def handle_evaluate_answer(args: dict) -> list[TextContent]:
    """Handle answer evaluation using the alignment metrics endpoint."""
    try:
        params = EvaluateAnswerParams(
            question=args["question"],
            answer=args["answer"],
            ground_truth_answer=args["ground_truth_answer"]
        )

        logger.info("Processing evaluate_answer request")

        response = _client.evaluate(params)

        # Format clean output: scores + per-fact reasoning + token usage
        output_lines = []

        # 1. Scores summary
        metrics = response.get("metrics", {})
        if isinstance(metrics, dict):
            alignment = metrics.get("alignment")
            correctness = metrics.get("correctness")
            completeness = metrics.get("completeness")
            output_lines.append("**Alignment Scores:**")
            if alignment is not None:
                output_lines.append(f"- Alignment (overall): {alignment:.3f}")
            if correctness is not None:
                output_lines.append(f"- Correctness (precision): {correctness:.3f}")
            if completeness is not None:
                output_lines.append(f"- Completeness (recall): {completeness:.3f}")

        # 2. Per-fact reasoning
        reasoning = response.get("reasoning", {})
        evaluated_facts = []
        if isinstance(reasoning, dict):
            evaluated_facts = reasoning.get("evaluated_facts", [])
        elif isinstance(reasoning, list):
            evaluated_facts = reasoning

        if evaluated_facts:
            output_lines.append("\n**Evaluated Facts:**")
            for item in evaluated_facts:
                if isinstance(item, dict):
                    fact = item.get("fact", {})
                    fact_content = fact.get("content", str(fact)) if isinstance(fact, dict) else str(fact)
                    entailment = item.get("entailment", {})
                    entailment_value = entailment.get("value", str(entailment)) if isinstance(entailment, dict) else str(entailment)
                    symbol = {"entailed": "✅", "contradicted": "❌", "neutral": "➖"}.get(entailment_value, "•")
                    output_lines.append(f"  {symbol} [{entailment_value}] {fact_content}")

        # 3. Token usage
        usage = response.get("usage", {})
        if usage and isinstance(usage, dict):
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", 0)
            if total:
                output_lines.append(
                    f"\n*Tokens: {prompt:,} prompt + {completion:,} completion = {total:,} total*"
                )

        return [TextContent(
            type="text",
            text="\n".join(output_lines)
        )]

    except Exception as e:
        logger.error(f"Evaluate answer request failed: {e}")
        raise


async def cleanup():
    """Cleanup server resources."""
    global _client

    if _client:
        AssistantClientManager.close()
        logger.info("Assistant client closed")


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting USPTO Pinecone Assistant MCP server")
    
    try:
        # Initialize server components
        await initialize()
        logger.info("Server initialization complete")
        
        # Run MCP server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
            
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        await cleanup()


def run_server() -> None:
    """Synchronous entry point for console script."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run_server()