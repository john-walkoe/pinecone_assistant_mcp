"""Configuration management for USPTO Pinecone Assistant MCP."""

import os
import re
import sys
import logging
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict

# Import secure storage functionality
try:
    from .secure_storage import get_secure_api_key
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from config.secure_storage import get_secure_api_key
    from util.secure_logging import setup_secure_logging

logger = setup_secure_logging(__name__, level=logging.INFO)


class Settings(BaseSettings):
    """Settings loaded from environment variables with validation."""
    
    # Required Pinecone Assistant settings
    pinecone_assistant_api_key: str = Field(
        default="", 
        description="Pinecone Assistant API key"
    )
    pinecone_assistant_host: str = Field(
        default="https://prod-1-data.ke.pinecone.io",
        description="Pinecone Assistant API host"
    )
    pinecone_assistant_name: str = Field(
        ...,
        description="Name of the Pinecone Assistant instance"
    )
    
    # Optional settings
    pinecone_assistant_model: str = Field(
        default="gpt-4o",
        description="Default AI model for responses"
    )
    debug_logging: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    
    # Timeout and retry settings
    request_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of request retries"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay between retries in seconds"
    )
    
    # Strategic search settings
    max_strategic_searches: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of strategic searches per request"
    )
    default_temperature: Optional[float] = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Default temperature for AI responses (0.2 for legal/USPTO precision, higher for creative domains)"
    )

    @field_validator('pinecone_assistant_api_key', mode='after')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format with enhanced security checks."""
        if not v:
            raise ValueError("Pinecone Assistant API key is required")

        # Check prefix
        if not v.startswith('pcsk_'):
            raise ValueError("Invalid Pinecone Assistant API key format. Must start with 'pcsk_'")

        # Check minimum length (Pinecone keys are typically 32+ characters)
        if len(v) < 32:
            raise ValueError("API key appears to be too short (minimum 32 characters)")

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^pcsk_[A-Za-z0-9_-]+$', v):
            raise ValueError("API key contains invalid characters")

        return v

    @field_validator('pinecone_assistant_host', mode='after')
    @classmethod
    def validate_host(cls, v):
        """Validate host URL format with HTTPS enforcement for production."""
        # Check basic URL format
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Host must be a valid URL starting with http:// or https://")

        # Get environment setting
        environment = os.getenv('ENVIRONMENT', 'development').lower()

        # Enforce HTTPS for production, allow HTTP only for localhost/127.0.0.1
        if environment == 'production':
            if not v.startswith('https://'):
                raise ValueError("Production environments must use HTTPS for secure connections")
        elif v.startswith('http://'):
            # Allow HTTP for localhost and 127.0.0.1 only
            if not ('localhost' in v or '127.0.0.1' in v):
                import logging
                logging.getLogger(__name__).warning(
                    "Using HTTP for non-localhost host. Consider using HTTPS for security."
                )

        return v.rstrip('/')  # Remove trailing slash

    @field_validator('pinecone_assistant_name', mode='after')
    @classmethod
    def validate_assistant_name(cls, v):
        """Validate assistant name format."""
        if not v:
            raise ValueError("Assistant name is required")
        if len(v) < 3:
            raise ValueError("Assistant name must be at least 3 characters")
        return v

    model_config = ConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        """Initialize settings with optional kwargs override."""
        # Try to get API key from secure storage BEFORE parent init
        if 'pinecone_assistant_api_key' not in kwargs or not kwargs.get('pinecone_assistant_api_key'):
            try:
                secure_key = get_secure_api_key()
                if secure_key:
                    kwargs['pinecone_assistant_api_key'] = secure_key
                    logger.info("API key loaded from secure storage")
                else:
                    logger.info("No API key in secure storage, checking environment variable")
            except Exception as e:
                # Log the failure but don't expose sensitive details
                logger.warning(
                    f"Failed to retrieve API key from secure storage: {type(e).__name__}. "
                    f"Falling back to PINECONE_ASSISTANT_API_KEY environment variable.",
                    extra={"error_type": type(e).__name__, "fallback": "environment_variable"}
                )

        # Now initialize with the secure key (if found)
        super().__init__(**kwargs)
        
        # Additional validation after initialization
        if not self.pinecone_assistant_name:
            raise ValueError(
                "PINECONE_ASSISTANT_NAME environment variable is required. "
                "This should be the name of your created Assistant instance."
            )

    @property
    def base_url(self) -> str:
        """Get the base URL for Assistant API calls."""
        return f"{self.pinecone_assistant_host}/assistant/chat/{self.pinecone_assistant_name}"

    @property
    def headers(self) -> dict:
        """Get the HTTP headers for API requests."""
        return {
            "Api-Key": self.pinecone_assistant_api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2025-10"
        }

    def get_model(self, override_model: Optional[str] = None) -> str:
        """Get the model to use, with optional override."""
        return override_model or self.pinecone_assistant_model

    def is_valid_model(self, model: str) -> bool:
        """Check if a model is supported by Pinecone Assistant.

        Supported as of 2026-02 (API version 2025-10):
        gpt-4o, gpt-4.1, gpt-5, o4-mini, claude-sonnet-4-5, gemini-2.5-pro.
        claude-3-5-sonnet and claude-3-7-sonnet are deprecated but Pinecone
        auto-routes them to claude-sonnet-4-5, so they still work.
        """
        supported_models = {
            "gpt-4o",
            "gpt-4.1",
            "gpt-5",
            "o4-mini",
            "claude-sonnet-4-5",
            "gemini-2.5-pro",
            # Deprecated, auto-routed to claude-sonnet-4-5 by Pinecone
            "claude-3-5-sonnet",
            "claude-3-7-sonnet",
        }
        return model in supported_models


def get_settings() -> Settings:
    """Get validated settings instance."""
    try:
        return Settings()
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")