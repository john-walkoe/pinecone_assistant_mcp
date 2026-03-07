"""
Unified Secure Storage for Pinecone API Keys

Architecture:
  - Shared credential across all 3 Pinecone MCPs (assistant, rag, diff_rag)
  - Windows Credential Manager target: "pinecone_API_KEY"
  - DPAPI file: ~/.pinecone_api_key (blob-only: DPAPI-encrypted key, no embedded entropy)
  - Entropy source: ~/.uspto_internal_auth_secret bytes 0-31 ("first wins" pattern)
  - Linux: ~/.pinecone_api_key plaintext with chmod 600

Security:
  - DPAPI per-user, per-machine encryption (Windows)
  - Cryptographically secure entropy via secrets.token_bytes(32)
  - Entropy stored separately in ~/.uspto_internal_auth_secret (NTFS ACL protected)
  - Blob-only format: smallest and fully cross-MCP compatible
  - No hardcoded entropy strings in production paths

See: C:\\Users\\John.WALKOE\\Claude_Documents\\SHARED_DPAPI_ENTROPY_PATTERN.md
"""

import base64
import ctypes
import ctypes.wintypes
import os
import sys
import secrets
import logging
from pathlib import Path
from typing import Optional

try:
    from ..util.secure_logging import setup_secure_logging
except ImportError:
    from util.secure_logging import setup_secure_logging

logger = setup_secure_logging(__name__, level=logging.INFO)

# ---------------------------------------------------------------------------
# Module-level constants — unified across all 3 Pinecone MCPs
# ---------------------------------------------------------------------------

PINECONE_API_KEY_FILE = Path.home() / ".pinecone_api_key"
INTERNAL_AUTH_SECRET_FILE = Path.home() / ".uspto_internal_auth_secret"
CREDENTIAL_TARGET = "pinecone_API_KEY"
CREDENTIAL_USER = "pinecone_API_KEY"


# ---------------------------------------------------------------------------
# Windows DPAPI low-level bindings
# ---------------------------------------------------------------------------

class DATA_BLOB(ctypes.Structure):
    """Windows DATA_BLOB structure for DPAPI operations."""
    _fields_ = [
        ('cbData', ctypes.wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_char))
    ]


def _get_data_from_blob(blob: DATA_BLOB) -> bytes:
    """Extract bytes from a DATA_BLOB structure."""
    if not blob.cbData:
        return b''
    cbData = int(blob.cbData)
    pbData = blob.pbData
    buffer = ctypes.create_string_buffer(cbData)
    ctypes.memmove(buffer, pbData, cbData)
    ctypes.windll.kernel32.LocalFree(pbData)
    return buffer.raw


def _encrypt_with_entropy(data: bytes, entropy_data: bytes, description: str = "Pinecone API Key") -> bytes:
    """
    Encrypt data using Windows DPAPI with provided entropy.

    Args:
        data: The data to encrypt (API key as bytes)
        entropy_data: Cryptographic entropy bytes (32 bytes recommended)
        description: Optional description for the encrypted data

    Returns:
        Encrypted data as bytes

    Raises:
        OSError: If encryption fails
        RuntimeError: If not running on Windows
    """
    if sys.platform != "win32":
        raise RuntimeError("DPAPI is only available on Windows")

    data_in = DATA_BLOB()
    data_in.pbData = ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char))
    data_in.cbData = len(data)

    data_out = DATA_BLOB()

    entropy = DATA_BLOB()
    entropy.pbData = ctypes.cast(ctypes.create_string_buffer(entropy_data), ctypes.POINTER(ctypes.c_char))
    entropy.cbData = len(entropy_data)

    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(data_in),
        description,
        ctypes.byref(entropy),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(data_out)
    )

    if not result:
        error_code = ctypes.windll.kernel32.GetLastError()
        raise OSError(f"CryptProtectData failed with error code: {error_code}")

    return _get_data_from_blob(data_out)


def _decrypt_with_entropy(encrypted_data: bytes, entropy_data: bytes) -> bytes:
    """
    Decrypt data using Windows DPAPI with provided entropy.

    Args:
        encrypted_data: The encrypted data to decrypt
        entropy_data: Cryptographic entropy bytes (must match encryption entropy)

    Returns:
        Decrypted data as bytes

    Raises:
        OSError: If decryption fails
        RuntimeError: If not running on Windows
    """
    if sys.platform != "win32":
        raise RuntimeError("DPAPI is only available on Windows")

    data_in = DATA_BLOB()
    data_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_data), ctypes.POINTER(ctypes.c_char))
    data_in.cbData = len(encrypted_data)

    data_out = DATA_BLOB()

    entropy = DATA_BLOB()
    entropy.pbData = ctypes.cast(ctypes.create_string_buffer(entropy_data), ctypes.POINTER(ctypes.c_char))
    entropy.cbData = len(entropy_data)

    description_ptr = ctypes.wintypes.LPWSTR()

    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(data_in),
        ctypes.byref(description_ptr),
        ctypes.byref(entropy),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(data_out)
    )

    if not result:
        error_code = ctypes.windll.kernel32.GetLastError()
        raise OSError(f"CryptUnprotectData failed with error code: {error_code}")

    if description_ptr.value:
        ctypes.windll.kernel32.LocalFree(description_ptr)

    return _get_data_from_blob(data_out)


# ---------------------------------------------------------------------------
# Deprecated legacy functions — kept for migrate_secure_entropy.py only
# ---------------------------------------------------------------------------

def encrypt_data(data: bytes, description: str = "Pinecone Assistant API Key") -> bytes:
    """
    DEPRECATED: Encrypt data using Windows DPAPI with hardcoded entropy.

    Kept for backward compatibility with migrate_secure_entropy.py only.
    Use SecureStorage.store_api_key() for all new code.
    """
    import warnings
    warnings.warn(
        "encrypt_data() uses hardcoded entropy (insecure). "
        "Use SecureStorage.store_api_key() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    entropy_data = b"pinecone_assistant_entropy_v1"
    return _encrypt_with_entropy(data, entropy_data, description)


def decrypt_data(encrypted_data: bytes) -> bytes:
    """
    DEPRECATED: Decrypt data using Windows DPAPI with hardcoded entropy.

    Kept for backward compatibility with migrate_secure_entropy.py only.
    Use SecureStorage.get_api_key() for all new code.
    """
    import warnings
    warnings.warn(
        "decrypt_data() uses hardcoded entropy (insecure). "
        "Use SecureStorage.get_api_key() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    entropy_data = b"pinecone_assistant_entropy_v1"
    return _decrypt_with_entropy(encrypted_data, entropy_data)


# ---------------------------------------------------------------------------
# Shared entropy: ~/.uspto_internal_auth_secret
# ---------------------------------------------------------------------------

def _get_or_create_internal_auth_entropy() -> bytes:
    """
    Get entropy from ~/.uspto_internal_auth_secret (bytes 0-31).

    "First wins" pattern:
    - If file exists (from any USPTO MCP or previous Pinecone MCP setup): use bytes 0-31
    - If not: generate the file (entropy prefix + DPAPI encrypted random secret) and return entropy

    Returns:
        32 bytes of cryptographically secure entropy
    """
    secret_file = INTERNAL_AUTH_SECRET_FILE

    if secret_file.exists():
        try:
            file_data = secret_file.read_bytes()
            if len(file_data) >= 32:
                logger.debug("Reusing existing ~/.uspto_internal_auth_secret entropy")
                return file_data[:32]
        except Exception as e:
            logger.warning(f"Could not read ~/.uspto_internal_auth_secret: {e}")

    # File does not exist or is malformed — generate it
    logger.info("Generating ~/.uspto_internal_auth_secret (first Pinecone MCP installation)")
    entropy = secrets.token_bytes(32)

    try:
        if sys.platform == "win32":
            secret_value = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            try:
                encrypted_secret = _encrypt_with_entropy(
                    secret_value.encode('utf-8'),
                    entropy,
                    "Pinecone Internal Auth Secret"
                )
                file_data = entropy + encrypted_secret
            except Exception as e:
                logger.warning(f"Could not DPAPI-encrypt internal auth secret: {e}; storing entropy prefix only")
                file_data = entropy + b"\x00" * 8
        else:
            # Linux/macOS: entropy prefix + plaintext secret
            secret_value = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            file_data = entropy + secret_value.encode('utf-8')

        secret_file.write_bytes(file_data)
        os.chmod(secret_file, 0o600)
        logger.info(f"Created ~/.uspto_internal_auth_secret at {secret_file}")
    except Exception as e:
        logger.warning(f"Could not persist ~/.uspto_internal_auth_secret: {e} (non-fatal)")

    return entropy


# ---------------------------------------------------------------------------
# SecureStorage class
# ---------------------------------------------------------------------------

class SecureStorage:
    """
    Unified secure storage for Pinecone API keys.

    Shared across all 3 Pinecone MCPs (pinecone_assistant_mcp, pinecone_rag_mcp,
    pinecone_diff_rag_mcp). All MCPs read/write the same ~/.pinecone_api_key file.

    Windows file format (blob-only):
      DPAPI-encrypted API key only — no embedded entropy.
      Entropy always comes from ~/.uspto_internal_auth_secret bytes 0-31.

    Linux: ~/.pinecone_api_key plaintext with chmod 600.
    """

    def __init__(self, storage_file: Optional[str] = None):
        """
        Initialize secure storage.

        Args:
            storage_file: Override path for storage file. Default: ~/.pinecone_api_key
        """
        if storage_file is None:
            self.storage_file = PINECONE_API_KEY_FILE
        else:
            self.storage_file = Path(storage_file)

        # entropy_file is always None — entropy comes from ~/.uspto_internal_auth_secret
        # Attribute kept as None for compatibility with any code that inspects it
        self.entropy_file = None

    def store_api_key(self, api_key: str) -> bool:
        """
        Store API key securely.

        Windows: DPAPI-encrypted with entropy from ~/.uspto_internal_auth_secret,
                 stored as blob-only (encrypted key only) in ~/.pinecone_api_key.
        Linux/macOS: plaintext in ~/.pinecone_api_key with chmod 600.

        Args:
            api_key: The Pinecone API key to store (must start with 'pcsk_')

        Returns:
            True if successful, False otherwise
        """
        try:
            if sys.platform != "win32":
                self.storage_file.write_text(api_key, encoding='utf-8')
                os.chmod(self.storage_file, 0o600)
                logger.info(f"API key stored at {self.storage_file} (chmod 600)")
                return True

            if not api_key.startswith("pcsk_"):
                raise ValueError("Invalid Pinecone API key format — must start with 'pcsk_'")

            # Get entropy from ~/.uspto_internal_auth_secret ("first wins")
            entropy_data = _get_or_create_internal_auth_entropy()

            # Encrypt
            encrypted_data = _encrypt_with_entropy(api_key.encode('utf-8'), entropy_data)

            # Write: blob-only (no embedded entropy — entropy lives in ~/.uspto_internal_auth_secret)
            if self.storage_file.exists():
                self.storage_file.unlink()
            self.storage_file.write_bytes(encrypted_data)
            os.chmod(self.storage_file, 0o600)

            logger.info(f"API key stored securely at {self.storage_file}")
            return True

        except ValueError as e:
            logger.error(f"Validation error storing API key: {e}")
            return False
        except OSError as e:
            logger.error(f"File system error storing API key: {e}",
                         extra={"error_type": "file_system", "error_code": getattr(e, 'errno', None)})
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing API key: {type(e).__name__}: {e}")
            return False

    def get_api_key(self) -> Optional[str]:
        """
        Retrieve API key from secure storage.

        Priority:
          Windows: ~/.pinecone_api_key (blob-only, legacy fallback) → PINECONE_API_KEY env → PINECONE_ASSISTANT_API_KEY env
          Linux:   ~/.pinecone_api_key (plaintext) → PINECONE_API_KEY env → PINECONE_ASSISTANT_API_KEY env

        Returns:
            The decrypted API key, or None if not found
        """
        try:
            if sys.platform != "win32":
                if self.storage_file.exists():
                    try:
                        api_key = self.storage_file.read_text(encoding='utf-8').strip()
                        if api_key.startswith("pcsk_"):
                            logger.debug(f"API key retrieved from {self.storage_file}")
                            return api_key
                    except Exception:
                        pass
                return (os.environ.get("PINECONE_API_KEY") or
                        os.environ.get("PINECONE_ASSISTANT_API_KEY"))

            # Windows: try blob-only format first, then legacy embedded-entropy format
            if self.storage_file.exists():
                try:
                    file_data = self.storage_file.read_bytes()
                    if len(file_data) > 0:
                        # Format 1 (current): blob-only, shared entropy from ~/.uspto_internal_auth_secret
                        try:
                            shared_entropy = _get_or_create_internal_auth_entropy()
                            decrypted = _decrypt_with_entropy(file_data, shared_entropy)
                            api_key = decrypted.decode('utf-8')
                            if api_key.startswith("pcsk_"):
                                logger.debug(f"API key retrieved from {self.storage_file}")
                                return api_key
                        except Exception:
                            pass
                        # Format 2 (legacy): [entropy32 | DPAPI blob]
                        if len(file_data) > 32:
                            try:
                                entropy = file_data[:32]
                                encrypted = file_data[32:]
                                decrypted = _decrypt_with_entropy(encrypted, entropy)
                                api_key = decrypted.decode('utf-8')
                                if api_key.startswith("pcsk_"):
                                    logger.debug(f"API key retrieved (legacy format) from {self.storage_file}")
                                    return api_key
                            except Exception:
                                pass
                except Exception as e:
                    logger.debug(f"Could not decrypt {self.storage_file}: {e}")

            # Fallback: environment variables
            return (os.environ.get("PINECONE_API_KEY") or
                    os.environ.get("PINECONE_ASSISTANT_API_KEY"))

        except Exception:
            return (os.environ.get("PINECONE_API_KEY") or
                    os.environ.get("PINECONE_ASSISTANT_API_KEY"))

    def has_secure_key(self) -> bool:
        """Check if a secure key is stored and valid."""
        try:
            api_key = self.get_api_key()
            return api_key is not None and api_key.startswith("pcsk_")
        except Exception:
            return False

    def remove_secure_key(self) -> bool:
        """Remove the secure key file."""
        try:
            if self.storage_file.exists():
                self.storage_file.unlink()
                logger.info(f"Removed {self.storage_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove secure key: {e}")
            return False


# ---------------------------------------------------------------------------
# Credential Manager integration
# ---------------------------------------------------------------------------

def get_api_key_from_credential_manager() -> Optional[str]:
    """
    Retrieve API key from Windows Credential Manager.

    Checks target "pinecone_API_KEY" (unified target for all 3 Pinecone MCPs).

    Returns:
        The API key, or None if not found
    """
    if sys.platform != "win32":
        return None

    try:
        import subprocess

        result = subprocess.run(
            [
                'powershell', '-NoProfile', '-NonInteractive', '-Command',
                f'''
                $ErrorActionPreference = 'SilentlyContinue'
                try {{
                    [void][Windows.Security.Credentials.PasswordVault,Windows.Security.Credentials,ContentType=WindowsRuntime]
                    $vault = New-Object Windows.Security.Credentials.PasswordVault
                    $allCreds = $vault.RetrieveAll()
                    foreach ($c in $allCreds) {{
                        if ($c.Resource -eq '{CREDENTIAL_TARGET}') {{
                            $c.RetrievePassword()
                            Write-Output $c.Password
                            exit 0
                        }}
                    }}
                }} catch {{ }}
                '''
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            api_key = result.stdout.strip()
            if api_key.startswith("pcsk_"):
                logger.debug(f"API key retrieved from Credential Manager target '{CREDENTIAL_TARGET}'")
                return api_key

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Public convenience functions
# ---------------------------------------------------------------------------

def get_secure_api_key() -> Optional[str]:
    """
    Get API key from secure storage.

    Priority:
    1. Windows Credential Manager (target: pinecone_API_KEY)
    2. DPAPI file ~/.pinecone_api_key (blob-only format, shared entropy)
    3. Env var PINECONE_API_KEY
    4. Env var PINECONE_ASSISTANT_API_KEY (legacy fallback)

    Returns:
        The API key, or None if not available
    """
    # Step 1: Windows Credential Manager
    api_key = get_api_key_from_credential_manager()
    if api_key:
        return api_key

    # Steps 2-4: DPAPI file then env vars
    storage = SecureStorage()
    return storage.get_api_key()


def store_secure_api_key(api_key: str) -> bool:
    """
    Store API key securely.

    Args:
        api_key: The Pinecone API key to store

    Returns:
        True if successful
    """
    storage = SecureStorage()
    return storage.store_api_key(api_key)


# ---------------------------------------------------------------------------
# CLI interface for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            print("Testing DPAPI encryption/decryption with unified credential architecture...")
            try:
                import tempfile
                with tempfile.TemporaryDirectory() as tmp:
                    storage = SecureStorage(storage_file=str(Path(tmp) / ".pinecone_api_key"))
                    test_data = "pcsk_test_key_123456789"

                    success = storage.store_api_key(test_data)
                    print(f"Store: {'SUCCESS' if success else 'FAILED'}")

                    retrieved = storage.get_api_key()
                    print(f"Retrieved: {retrieved[:10]}..." if retrieved else "FAILED to retrieve")

                    if retrieved == test_data:
                        print("[SUCCESS] DPAPI test PASSED")
                    else:
                        print("[FAILED] DPAPI test FAILED")

            except Exception as e:
                print(f"[FAILED] DPAPI test FAILED: {e}")

        elif sys.argv[1] == "store":
            if len(sys.argv) > 2:
                # Accepting via argv for CLI convenience — for production, use stdin
                import warnings
                warnings.warn("Passing API key as argument may expose it in process list. "
                              "Prefer stdin input.", UserWarning)
                success = store_secure_api_key(sys.argv[2])
                print("[SUCCESS] API key stored securely" if success else "[FAILED] Failed to store API key")
            elif not sys.stdin.isatty():
                api_key = sys.stdin.read().strip()
                success = store_secure_api_key(api_key)
                print("[SUCCESS] API key stored securely" if success else "[FAILED] Failed to store API key")
            else:
                import getpass
                api_key = getpass.getpass("Enter API key: ")
                success = store_secure_api_key(api_key)
                print("[SUCCESS] API key stored securely" if success else "[FAILED] Failed to store API key")

        elif sys.argv[1] == "get":
            api_key = get_secure_api_key()
            if api_key:
                print(f"API key: {api_key[:10]}...")
            else:
                print("No API key found")

        elif sys.argv[1] == "info":
            print(f"Credential target:   {CREDENTIAL_TARGET}")
            print(f"Key file:            {PINECONE_API_KEY_FILE}")
            print(f"Entropy source:      {INTERNAL_AUTH_SECRET_FILE}")
            print(f"Key file exists:     {PINECONE_API_KEY_FILE.exists()}")
            print(f"Entropy file exists: {INTERNAL_AUTH_SECRET_FILE.exists()}")

    else:
        print("Usage:")
        print("  python secure_storage.py test       - Test DPAPI functionality")
        print("  python secure_storage.py store <key> - Store API key")
        print("  python secure_storage.py get         - Retrieve API key")
        print("  python secure_storage.py info        - Show storage info")
