"""
Configuration and secure storage module.

Manages application settings via environment variables and secure credential storage.
Provides Pydantic-based validation for API keys, hosts, and configuration parameters.

Components:
    - Settings: Pydantic settings with validation
    - get_settings: Cached settings factory
    - SecureStorage: Platform-specific secure credential storage (Windows DPAPI, etc.)

Security Features:
    - API key format validation (prefix, length, characters)
    - HTTPS enforcement for production
    - Secure credential storage integration
"""

from .config import Settings, get_settings
from .secure_storage import (
    get_secure_api_key,
    store_secure_api_key,
    SecureStorage,
)

__all__ = [
    "Settings",
    "get_settings",
    "get_secure_api_key",
    "store_secure_api_key",
    "SecureStorage",
]
