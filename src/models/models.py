"""Type definitions for USPTO Pinecone Assistant MCP."""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class Message(BaseModel):
    """A chat message with role and content."""
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=100000)  # Max 100KB per message

    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v):
        """Validate message content doesn't exceed maximum length."""
        if len(v) > 100000:
            raise ValueError("Message content exceeds maximum length (100KB)")
        return v


class AssistantChatParams(BaseModel):
    """Parameters for assistant chat requests."""
    messages: List[Message] = Field(..., max_length=50)  # Max 50 messages
    model: str = Field(default="gpt-4o", description="AI model to use")
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Response randomness"
    )
    include_highlights: bool = Field(
        default=True, description="Include citation highlights"
    )
    stream: bool = Field(default=False, description="Enable streaming responses")
    filter: Optional[Dict[str, Any]] = Field(
        default=None, description="Document metadata filter for scoping chat to specific documents"
    )
    json_response: bool = Field(
        default=False, description="Request structured JSON output from the assistant"
    )
    context_options: Optional[Dict[str, int]] = Field(
        default=None,
        description="Limit context sent to LLM: {'top_k': N, 'snippet_size': N}. API defaults: top_k=16, snippet_size=2048."
    )

    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        """Validate message list constraints."""
        if not v:
            raise ValueError("At least one message is required")
        if len(v) > 50:
            raise ValueError("Maximum 50 messages per request")

        # Check total content size
        total_chars = sum(len(m.content) for m in v)
        if total_chars > 500000:  # 500KB total
            raise ValueError("Total message content exceeds maximum size (500KB)")

        return v


class StrategySearchParams(BaseModel):
    """Parameters for strategic multi-search requests."""
    query: str = Field(description="Primary research question")
    domain: str = Field(
        default="core_examination_framework", description="Search pattern domain"
    )
    max_searches: Optional[int] = Field(
        default=None, ge=1, le=20, description="Maximum number of searches"
    )
    model: str = Field(default="gpt-4o", description="AI model to use")


class AssistantConfig(BaseModel):
    """Configuration for Pinecone Assistant API."""
    api_key: str = Field(description="Pinecone Assistant API key")
    host: str = Field(description="Pinecone Assistant API host")
    assistant_name: str = Field(description="Assistant instance name")
    default_model: str = Field(default="gpt-4o", description="Default AI model")
    debug_logging: bool = Field(default=False, description="Enable debug logging")


class SearchPattern(BaseModel):
    """A single search pattern from YAML configuration."""
    name: str
    query: str
    description: str
    enabled: bool = True


class SearchDomain(BaseModel):
    """A domain containing multiple search patterns."""
    searches: List[SearchPattern]


class HighlightedText(BaseModel):
    """Text with citation highlighting."""
    text: str
    highlights: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class AssistantResponse(BaseModel):
    """Response from Pinecone Assistant."""
    content: str
    highlights: Optional[HighlightedText] = None
    usage: Optional[Dict[str, Any]] = None
    model: str
    finish_reason: Optional[str] = None


class AssistantContextParams(BaseModel):
    """Parameters for assistant context retrieval requests."""
    query: Optional[str] = Field(default=None, description="Query for context retrieval (required if messages not provided)")
    top_k: int = Field(default=5, ge=1, le=64, description="Number of context snippets")
    snippet_size: int = Field(default=2048, ge=512, le=8192, description="Tokens per snippet")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filter")
    multimodal: Optional[bool] = Field(default=None, description="Enable multimodal context (images from PDFs). API default: true.")
    include_binary_content: Optional[bool] = Field(default=None, description="Include base64 image data in response. API default: true.")
    messages: Optional[List[Dict[str, str]]] = Field(default=None, description="Multi-turn messages as alternative to query (role/content pairs)")

    @model_validator(mode='after')
    def validate_query_or_messages(self):
        """Require either query or messages."""
        if not self.query and not self.messages:
            raise ValueError("Either 'query' or 'messages' is required for context retrieval")
        return self


class ContextSnippet(BaseModel):
    """A context snippet from document retrieval."""
    type: str = Field(description="Snippet type")
    content: str = Field(description="Snippet content")
    score: float = Field(description="Relevancy score")
    reference: Dict[str, Any] = Field(description="Source reference")


class AssistantContextResponse(BaseModel):
    """Response from context retrieval."""
    id: Optional[str] = None
    snippets: List[ContextSnippet]
    usage: Optional[Dict[str, Any]] = None


class StrategyContextParams(BaseModel):
    """Parameters for strategic multi-search context requests."""
    query: str = Field(description="Primary research question")
    domain: str = Field(
        default="core_examination_framework", description="Search pattern domain"
    )
    max_searches: Optional[int] = Field(
        default=None, ge=1, le=20, description="Maximum number of searches"
    )
    top_k: int = Field(default=5, ge=1, le=64, description="Snippets per search")
    snippet_size: int = Field(default=2048, ge=512, le=8192, description="Tokens per snippet")


class ContextSearchResult(BaseModel):
    """Result from a single context search."""
    pattern_name: str
    query_executed: str
    snippets: List[ContextSnippet]
    snippet_count: int


class StrategyContextResult(BaseModel):
    """Result from strategic multi-search context execution."""
    query: str
    domain: str
    searches_executed: List[str]
    results: List[ContextSearchResult]
    total_snippets: int = 0
    unique_sources: int = 0


class StrategicSearchResult(BaseModel):
    """Result from a strategic search execution."""
    query: str
    domain: str
    searches_executed: List[str]
    results: List[AssistantResponse]
    summary: Optional[str] = None
    total_sources: int = 0


class EvaluateAnswerParams(BaseModel):
    """Parameters for answer evaluation requests."""
    question: str = Field(description="The question that was asked")
    answer: str = Field(description="The generated answer to evaluate")
    ground_truth_answer: str = Field(description="The correct/expected answer to compare against")