"""
Tests for the unified Pinecone credential architecture.

Verifies that pinecone_assistant_mcp uses the shared credential names and patterns
that will be adopted by pinecone_rag_mcp and pinecone_diff_rag_mcp.

See: C:\\Users\\John.WALKOE\\Claude_Documents\\PINECONE_UNIFIED_CREDENTIAL_ARCHITECTURE.md
"""

import os
import secrets
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.secure_storage import (
    CREDENTIAL_TARGET,
    CREDENTIAL_USER,
    INTERNAL_AUTH_SECRET_FILE,
    PINECONE_API_KEY_FILE,
    SecureStorage,
    _get_or_create_internal_auth_entropy,
    get_secure_api_key,
)


class TestUnifiedCredentialConstants:
    """Verify the module-level constants match the unified architecture spec."""

    def test_credential_target_is_pinecone_api_key(self):
        """Windows Credential Manager target must be 'pinecone_API_KEY'."""
        assert CREDENTIAL_TARGET == "pinecone_API_KEY", (
            f"Expected 'pinecone_API_KEY', got {CREDENTIAL_TARGET!r}. "
            "All 3 Pinecone MCPs must use the same Credential Manager target."
        )

    def test_credential_user_is_pinecone_api_key(self):
        """Windows Credential Manager user field must be 'pinecone_API_KEY'."""
        assert CREDENTIAL_USER == "pinecone_API_KEY"

    def test_storage_file_is_shared_pinecone_api_key(self):
        """DPAPI file must be ~/.pinecone_api_key (shared across all 3 MCPs)."""
        assert str(PINECONE_API_KEY_FILE).endswith(".pinecone_api_key"), (
            f"Expected path ending with .pinecone_api_key, got {PINECONE_API_KEY_FILE}"
        )
        # Must NOT be the old per-MCP file
        assert "pinecone_assistant" not in str(PINECONE_API_KEY_FILE), (
            "Storage file must not be the old per-MCP pinecone_assistant file"
        )

    def test_entropy_source_is_uspto_internal_auth_secret(self):
        """Entropy source must be ~/.uspto_internal_auth_secret (shared with USPTO MCPs)."""
        assert str(INTERNAL_AUTH_SECRET_FILE).endswith(".uspto_internal_auth_secret"), (
            f"Expected path ending with .uspto_internal_auth_secret, got {INTERNAL_AUTH_SECRET_FILE}"
        )

    def test_entropy_file_attribute_is_none(self):
        """SecureStorage.entropy_file must be None — no separate entropy file in new arch."""
        storage = SecureStorage()
        assert storage.entropy_file is None, (
            "entropy_file must be None. Entropy is now embedded in ~/.pinecone_api_key "
            "and sourced from ~/.uspto_internal_auth_secret."
        )

    def test_no_old_per_mcp_credential_name_in_code(self):
        """Verify old credential name is gone from the implementation."""
        secure_storage_path = Path(__file__).parent.parent / "src" / "config" / "secure_storage.py"
        code = secure_storage_path.read_text()
        assert "pinecone-assistant-mcp_API_KEY" not in code, (
            "Old per-MCP credential name must be removed from secure_storage.py"
        )

    def test_no_old_storage_file_path_in_code(self):
        """Verify old storage file path is gone from the implementation."""
        secure_storage_path = Path(__file__).parent.parent / "src" / "config" / "secure_storage.py"
        code = secure_storage_path.read_text()
        assert ".pinecone_assistant_secure_key" not in code, (
            "Old storage file path (.pinecone_assistant_secure_key) must be removed"
        )


class TestInternalAuthSecretEntropy:
    """Verify ~/.uspto_internal_auth_secret is used as the shared entropy source."""

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_creates_auth_secret_file_if_missing(self, tmp_path):
        """If ~/.uspto_internal_auth_secret doesn't exist, it should be created."""
        auth_path = tmp_path / ".test_auth_secret"
        assert not auth_path.exists()

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy = _get_or_create_internal_auth_entropy()

        assert auth_path.exists(), "~/.uspto_internal_auth_secret should be created"
        assert len(entropy) == 32, "Entropy must be 32 bytes"

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_reuses_existing_auth_secret_file(self, tmp_path):
        """If ~/.uspto_internal_auth_secret exists (e.g., from USPTO MCP), reuse it."""
        auth_path = tmp_path / ".test_auth_secret"
        known_entropy = secrets.token_bytes(32)
        # Simulate existing file (as USPTO MCPs would create it)
        auth_path.write_bytes(known_entropy + b"\x00" * 16)

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy = _get_or_create_internal_auth_entropy()

        assert entropy == known_entropy, (
            "Must reuse bytes 0-31 from existing ~/.uspto_internal_auth_secret. "
            "This ensures compatibility with USPTO MCPs."
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_auth_secret_file_is_at_least_32_bytes(self, tmp_path):
        """~/.uspto_internal_auth_secret must store at least 32 bytes (entropy prefix)."""
        auth_path = tmp_path / ".test_auth_secret"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            _get_or_create_internal_auth_entropy()

        file_data = auth_path.read_bytes()
        assert len(file_data) >= 32, "Auth secret file must be at least 32 bytes"

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_auth_secret_entropy_is_cryptographically_random(self, tmp_path):
        """Verify two separate generations produce different entropy (not deterministic)."""
        auth1 = tmp_path / ".auth1"
        auth2 = tmp_path / ".auth2"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth1):
            e1 = _get_or_create_internal_auth_entropy()

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth2):
            e2 = _get_or_create_internal_auth_entropy()

        assert e1 != e2, "Independent entropy generations must produce different values"


class TestSharedKeyFile:
    """Verify the key file is shared-compatible (same format across all 3 Pinecone MCPs)."""

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_key_file_uses_embedded_entropy_format(self, tmp_path):
        """
        Key file format: bytes 0-31 = entropy, bytes 32+ = DPAPI encrypted key.

        This format allows the file to be self-contained for decryption and
        is consistent with the USPTO ~/.uspto_api_key format.
        """
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            storage.store_api_key("pcsk_test_unified_format_" + "u" * 30)

        file_data = key_path.read_bytes()
        assert len(file_data) > 32, (
            "Key file must have format: [entropy 32 bytes] + [encrypted key N bytes]. "
            "Got file with only 32 bytes or less."
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI: Windows only")
    def test_key_file_is_self_contained_for_decryption(self, tmp_path):
        """
        Decryption must work using only the key file itself (entropy embedded in bytes 0-31).
        ~/.uspto_internal_auth_secret is NOT needed at read time.
        """
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"
        test_key = "pcsk_self_contained_test_" + "s" * 30

        # Store with auth secret
        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            storage.store_api_key(test_key)

        # Retrieve WITHOUT auth secret being present (it's embedded in key file)
        # (We still need the patch to avoid reading the real ~/.uspto_internal_auth_secret)
        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", tmp_path / ".nonexistent"):
            storage2 = SecureStorage(storage_file=str(key_path))
            retrieved = storage2.get_api_key()

        assert retrieved == test_key, (
            "Decryption must work using entropy embedded in the key file (bytes 0-31). "
            "~/.uspto_internal_auth_secret is not needed at read time."
        )


class TestEnvVarFallbackChain:
    """Verify the retrieval priority chain includes both env var names."""

    def test_pinecone_api_key_env_var_is_primary(self):
        """PINECONE_API_KEY env var must work as primary fallback."""
        test_key = "pcsk_env_var_primary_" + "p" * 30

        non_existent_key_file = "/nonexistent/.pinecone_api_key"
        non_existent_auth_file = "/nonexistent/.uspto_internal_auth_secret"

        with patch("src.config.secure_storage.PINECONE_API_KEY_FILE", Path(non_existent_key_file)):
            with patch("src.config.secure_storage.get_api_key_from_credential_manager", return_value=None):
                with patch.dict(os.environ, {"PINECONE_API_KEY": test_key}, clear=False):
                    storage = SecureStorage(storage_file=non_existent_key_file)
                    key = storage.get_api_key()

        assert key == test_key, "PINECONE_API_KEY env var must be used as fallback"

    def test_pinecone_assistant_api_key_is_legacy_fallback(self):
        """PINECONE_ASSISTANT_API_KEY env var must work as secondary fallback."""
        test_key = "pcsk_legacy_fallback_" + "l" * 30

        non_existent_key_file = "/nonexistent/.pinecone_api_key"

        with patch("src.config.secure_storage.PINECONE_API_KEY_FILE", Path(non_existent_key_file)):
            with patch("src.config.secure_storage.get_api_key_from_credential_manager", return_value=None):
                # Explicitly unset PINECONE_API_KEY but set the legacy var
                env = {k: v for k, v in os.environ.items()
                       if k not in ("PINECONE_API_KEY", "PINECONE_ASSISTANT_API_KEY")}
                env["PINECONE_ASSISTANT_API_KEY"] = test_key

                with patch.dict(os.environ, env, clear=True):
                    storage = SecureStorage(storage_file=non_existent_key_file)
                    key = storage.get_api_key()

        assert key == test_key, "PINECONE_ASSISTANT_API_KEY must work as legacy fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
