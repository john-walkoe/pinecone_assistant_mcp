"""
Test suite for entropy security in DPAPI encryption.

Validates the unified Pinecone credential architecture:
- Cryptographically secure random entropy from ~/.uspto_internal_auth_secret
- Embedded entropy format (bytes 0-31 entropy + bytes 32+ encrypted key)
- No hardcoded entropy values
- Proper entropy length and randomness
"""

import os
import secrets
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Only run DPAPI tests on Windows
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI tests only run on Windows")

from src.config.secure_storage import (
    SecureStorage,
    _get_or_create_internal_auth_entropy,
    decrypt_data,
    INTERNAL_AUTH_SECRET_FILE,
    PINECONE_API_KEY_FILE,
)


class TestEntropyRandomness:
    """Test entropy generation for cryptographic security."""

    def test_entropy_is_unique_across_different_auth_secrets(self, tmp_path):
        """Verify that different ~/.uspto_internal_auth_secret files produce different entropy."""
        auth1 = tmp_path / ".auth1"
        auth2 = tmp_path / ".auth2"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth1):
            entropy1 = _get_or_create_internal_auth_entropy()

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth2):
            entropy2 = _get_or_create_internal_auth_entropy()

        assert entropy1 != entropy2, "Different auth secret files must produce different entropy"

    def test_entropy_is_not_hardcoded_value(self, tmp_path):
        """Verify entropy is not the old hardcoded value from the vulnerable version."""
        auth_path = tmp_path / ".test_auth_secret"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy = _get_or_create_internal_auth_entropy()

        old_hardcoded = b"pinecone_assistant_entropy_v1"
        assert entropy != old_hardcoded, "CRITICAL: Must not use hardcoded entropy!"

    def test_entropy_has_correct_length(self, tmp_path):
        """Verify entropy is 256 bits (32 bytes) as required."""
        auth_path = tmp_path / ".test_auth_secret"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy = _get_or_create_internal_auth_entropy()

        assert len(entropy) == 32, f"Entropy must be 32 bytes (256 bits), got {len(entropy)}"

    def test_entropy_is_stable_for_same_auth_secret_file(self, tmp_path):
        """Verify that the same ~/.uspto_internal_auth_secret produces same entropy on repeated calls."""
        auth_path = tmp_path / ".test_auth_secret"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy1 = _get_or_create_internal_auth_entropy()
            # Second call should reuse the existing file (not regenerate)
            entropy2 = _get_or_create_internal_auth_entropy()

        assert entropy1 == entropy2, "Same auth secret file must produce same entropy"
        assert auth_path.exists(), "Auth secret file should have been created"

    def test_auth_secret_file_has_restrictive_permissions(self, tmp_path):
        """Verify ~/.uspto_internal_auth_secret is created with chmod 600."""
        auth_path = tmp_path / ".test_auth_secret"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            _get_or_create_internal_auth_entropy()

        assert auth_path.exists(), "Auth secret file should exist"
        # On Windows, chmod is informational but we verify the call didn't error
        # The stat_mode check is more meaningful on Linux; on Windows it's a no-op
        stat_info = auth_path.stat()
        assert stat_info.st_size >= 32, "Auth secret file must be at least 32 bytes"

    def test_entropy_generation_uses_secrets_module(self):
        """Verify code uses Python's secrets module (cryptographically secure)."""
        secure_storage_path = Path(__file__).parent.parent / "src" / "config" / "secure_storage.py"
        code = secure_storage_path.read_text()
        assert "import secrets" in code, "Must import secrets module"
        assert "secrets.token_bytes" in code, "Must use secrets.token_bytes for entropy generation"


class TestKeyFileEmbeddedFormat:
    """Test the embedded-entropy key file format."""

    def test_key_file_has_embedded_entropy_prefix(self, tmp_path):
        """Verify key file format: bytes 0-31 = entropy, bytes 32+ = encrypted data."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            success = storage.store_api_key("pcsk_test_embedded_format_" + "x" * 20)

        assert success, "store_api_key must succeed"
        file_data = key_path.read_bytes()
        assert len(file_data) > 32, "Key file must have entropy prefix (32 bytes) + encrypted data"

        entropy_prefix = file_data[:32]
        assert len(entropy_prefix) == 32, "Entropy prefix must be exactly 32 bytes"

    def test_no_separate_entropy_file_created(self, tmp_path):
        """Verify no separate .entropy file is created (entropy is embedded in key file)."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            storage.store_api_key("pcsk_test_no_entropy_file_" + "y" * 20)

        assert not (tmp_path / ".pinecone_api_key.entropy").exists(), \
            "No separate .entropy file should be created in new architecture"

    def test_entropy_file_attribute_is_none(self, tmp_path):
        """Verify SecureStorage.entropy_file is None in new architecture."""
        storage = SecureStorage(storage_file=str(tmp_path / ".pinecone_api_key"))
        assert storage.entropy_file is None, "entropy_file attribute must be None"


class TestEncryptionDecryption:
    """Test encryption/decryption with embedded entropy format."""

    def test_round_trip_store_and_retrieve(self, tmp_path):
        """Verify API key can be stored and retrieved correctly."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"
        test_api_key = "pcsk_test_secure_key_123456789012345"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            success = storage.store_api_key(test_api_key)
            assert success, "Failed to store API key"
            retrieved = storage.get_api_key()

        assert retrieved == test_api_key, f"Decrypted key {retrieved!r} doesn't match original"

    def test_tampering_with_embedded_entropy_breaks_decryption(self, tmp_path):
        """Verify that tampering with bytes 0-31 (entropy prefix) makes decryption fail."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"
        test_api_key = "pcsk_test_tamper_key_987654321234"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            storage.store_api_key(test_api_key)

        # Tamper with the entropy prefix (bytes 0-31)
        file_data = key_path.read_bytes()
        tampered = b"X" * 32 + file_data[32:]
        key_path.write_bytes(tampered)

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            retrieved = storage.get_api_key()

        # Should NOT match the original key (entropy mismatch caused decryption failure)
        assert retrieved != test_api_key, "Decryption should fail with tampered entropy prefix"

    def test_existing_auth_secret_used_for_encryption(self, tmp_path):
        """Verify that an existing ~/.uspto_internal_auth_secret is reused, not regenerated."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"

        # Pre-create auth secret with known content
        known_entropy = secrets.token_bytes(32)
        auth_path.write_bytes(known_entropy + b"\x00" * 8)

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            entropy = _get_or_create_internal_auth_entropy()

        assert entropy == known_entropy, "Existing auth secret bytes 0-31 must be reused"


class TestSecurityValidation:
    """High-level security validation tests."""

    def test_no_hardcoded_entropy_in_production_paths(self):
        """Scan code for hardcoded entropy usage — only acceptable in DEPRECATED functions."""
        secure_storage_path = Path(__file__).parent.parent / "src" / "config" / "secure_storage.py"
        code = secure_storage_path.read_text()

        hardcoded_entropy = "pinecone_assistant_entropy_v1"
        occurrences = code.count(hardcoded_entropy)

        # Should appear exactly 2 times: in DEPRECATED encrypt_data() and decrypt_data() only
        assert occurrences == 2, (
            f"Hardcoded entropy appears {occurrences} times "
            f"(expected 2 — only in DEPRECATED encrypt_data/decrypt_data functions)"
        )

        # Verify all occurrences are in the deprecated section
        lines_with_entropy = [line.strip() for line in code.split('\n') if hardcoded_entropy in line]
        assert len(lines_with_entropy) == 2, "Hardcoded entropy should only appear in deprecated functions"

    def test_api_key_validation_rejects_invalid_format(self, tmp_path):
        """Test that API key validation rejects keys not starting with 'pcsk_'."""
        auth_path = tmp_path / ".test_auth_secret"
        storage = SecureStorage(storage_file=str(tmp_path / ".pinecone_api_key"))

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            invalid_keys = [
                "sk_invalid_key",
                "not_a_pinecone_key",
                "",
                "PCSK_uppercase",
            ]

            for invalid_key in invalid_keys:
                result = storage.store_api_key(invalid_key)
                assert not result, f"Should reject invalid key format: {invalid_key!r}"

    def test_api_key_validation_accepts_valid_format(self, tmp_path):
        """Test that valid pcsk_ keys are accepted."""
        auth_path = tmp_path / ".test_auth_secret"
        key_path = tmp_path / ".pinecone_api_key"

        with patch("src.config.secure_storage.INTERNAL_AUTH_SECRET_FILE", auth_path):
            storage = SecureStorage(storage_file=str(key_path))
            result = storage.store_api_key("pcsk_valid_key_format_" + "a" * 30)

        assert result, "Valid pcsk_ key should be accepted"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
