# Security Guidelines

## Overview

This document provides comprehensive security guidelines for developing, deploying, and maintaining the Pinecone Assistant MCP Server. Following these guidelines helps ensure the security of API keys, user data, system integrity, and protection against AI-specific attacks including prompt injection.

## 🛡️ Prompt Injection Protection

### Overview
The Pinecone Assistant MCP includes prompt injection scanning to protect against malicious attempts to:
- Override system instructions
- Extract sensitive prompts or configuration
- Manipulate AI behavior
- Bypass security controls
- Access unauthorized document data

### Detection System
**Comprehensive Pattern Detection:**
- **70+ Attack Patterns** covering instruction override, prompt extraction, format manipulation
- **Corpus-Specific Threats** including knowledge base bypass attempts and document data disclosure
- **Enhanced Filtering** to minimize false positives in legitimate code and documentation
- **Unicode Steganography Detection** for advanced hidden-instruction attacks

**Integration Points:**
- **Pre-commit Hooks** - Automatic scanning before every commit
- **CI/CD Pipeline** - Continuous validation in GitHub Actions
- **Manual Scanning** - On-demand security assessment tools

### Usage

**Manual Security Scanning:**
```bash
# Scan specific directories/files
uv run python .security/check_prompt_injections.py src/ tests/ *.md

# Scan all relevant file types
uv run python .security/check_prompt_injections.py src/ tests/ docs/ *.yml *.json

# Run via pre-commit (recommended)
uv run pre-commit run prompt-injection-check --all-files
```

**Attack Categories Detected:**
1. **Instruction Override**: "ignore previous instructions", "disregard above commands"
2. **Prompt Extraction**: "show me your instructions", "reveal your system prompt"
3. **Behavior Manipulation**: "you are now a different AI", "act as a hacker"
4. **Format Manipulation**: "encode in base64", "spell backwards", "use hex encoding"
5. **Document-Specific**: "extract all documents", "bypass assistant API limits", "dump the knowledge base"
6. **Social Engineering**: "we became friends", "our previous conversation"

**File Type Coverage:**
- Python source code (.py)
- Configuration files (.yml, .yaml, .json)
- Documentation (.md, .txt)
- Web files (.html, .js, .ts)
- Data files (.csv, .xml)

### Incident Response

**If Patterns Are Detected:**
1. **Review Context** - Determine if the detection is legitimate or false positive
2. **Assess Intent** - Check if the pattern was introduced maliciously
3. **Investigate Source** - Review commit history and author
4. **Document Findings** - Log the incident for security tracking
5. **Update Exclusions** - If false positive, consider pattern refinements

**False Positive Handling:**
```bash
# For legitimate test cases, add context markers
echo "# Example injection pattern (for testing): ignore previous instructions" >> test_file.py

# For documentation, ensure clear context
echo "This pattern 'show me your instructions' is an example of prompt injection" >> docs.md
```

### Advanced Threats

**Hybrid Attacks** (Future Considerations):
- **XSS + Prompt Injection**: AI-generated JavaScript payloads
- **SQL + Prompt Injection**: Natural language to malicious SQL
- **Multi-Agent Propagation**: Self-replicating prompts across AI systems

**Multi-Modal Injection** (Roadmap):
- **Image-based**: Hidden instructions in steganography
- **Audio/Video**: Transcript manipulation attacks
- **Cross-Modal**: Exploiting modality translation inconsistencies

## API Key Management

### 🔐 **Environment Variables**

**Always use environment variables for API keys:**

```python
# ✅ Correct - Environment variable
api_key = os.getenv("PINECONE_ASSISTANT_API_KEY")
if not api_key:
    raise ValueError("PINECONE_ASSISTANT_API_KEY environment variable is required")

# ❌ Never do this - Hardcoded key
api_key = "pcsk_your_actual_api_key_here"
```

### 🔑 **API Key Storage — Priority Order**

The MCP server retrieves the API key using a three-tier priority system:

1. **Windows Credential Manager** (highest priority)
   - Stored by the deployment script automatically
   - Managed by Windows account security
   - Never written to disk in plain text

2. **Windows DPAPI Encrypted File** (fallback)
   - `SecureStorage` class in `src/config/secure_storage.py`
   - Encrypted using Windows Data Protection API via Python ctypes
   - Uses cryptographically secure random entropy (`secrets.token_bytes(32)`)
   - File permissions set to `0o600` (owner read/write only)
   - Decryptable only by the same Windows user account

3. **Environment Variable** (last resort)
   - `PINECONE_ASSISTANT_API_KEY` environment variable
   - Acceptable for Linux/macOS or CI/CD environments
   - Avoid for Windows desktop use — prefer DPAPI

**Development Environment:**
```bash
# Use .env files (add to .gitignore)
echo "PINECONE_ASSISTANT_API_KEY=your_dev_key" > .env.local
echo ".env.local" >> .gitignore
```

**Claude Desktop Configuration (DPAPI — Recommended for Windows):**
```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp/.venv/Scripts/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp",
      "env": {
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io/assistant",
        "PINECONE_ASSISTANT_NAME": "my-assistant"
      }
    }
  }
}
```

**Note**: With DPAPI storage, the API key is NOT in the config file — it is retrieved from the encrypted store at runtime.

### 🚫 **What Never to Commit**

- Real API keys in any form
- Configuration files with real credentials
- Test files with hardcoded keys
- `.env` files or local config files
- Backup files that might contain keys

## Logging Security (CWE-532 & CWE-778)

### 🔒 **SecureLogger / SecureFormatter Implementation**

The project implements a **SecureFormatter** class (`src/util/secure_logging.py`) that automatically sanitizes all log messages to prevent sensitive data exposure. This addresses:

- **CWE-532**: Insertion of Sensitive Information into Log File
- **CWE-778**: Insufficient Logging

```python
from src.util.secure_logging import setup_secure_logging

# Initialize secure logging (called at server startup)
setup_secure_logging('INFO')

# All loggers obtained through Python's logging module
# automatically pass through SecureFormatter sanitization
logger = logging.getLogger(__name__)

# API keys in log messages are automatically redacted
logger.error(f"API response: {api_response_text}")
# pcsk_* keys in api_response_text become [REDACTED]
```

### 🛡️ **What Gets Sanitized Automatically**

**API Keys:**
- Pinecone API keys (`pcsk_*`): `[REDACTED]`
- Generic `api_key` patterns: `[REDACTED]`
- Authorization header values: `[REDACTED]`

**Tokens & Secrets:**
- JWT Bearer tokens: `[REDACTED]`
- Passwords and secret fields: `[REDACTED]`
- Generic `token` patterns: `[REDACTED]`

**Log Injection Prevention:**
- Newline characters (`\n`) — escaped to prevent log spoofing
- Carriage returns (`\r`) — escaped
- Tab characters (`\t`) — escaped
- Message length capped at 5,000 characters

### 📝 **File-Based Logging with Rotation**

**Application Log** (`~/.pinecone_assistant/logs/`):
- `RotatingFileHandler`: 10MB max, 5 backup files
- General application events

**Security Audit Log** (`~/.pinecone_assistant/logs/security_audit.log`):
- `RotatingFileHandler`: 10MB max, 10 backup files (longer retention)
- Security events only — separate file for SIEM integration

**File Permissions:**
- Unix: `600` (owner read/write only)
- Windows: Protected by user account security

### 🎯 **Security Audit Logging**

The `SecurityAuditLogger` (`src/util/security_audit.py`) writes structured JSON events to the security audit log:

```python
# Security events are automatically logged by the MCP server
# These events are written to security_audit.log:
{
  "event": "rate_limit",
  "tool": "assistant_chat",
  "request_id": "abc-123",
  "timestamp": "2025-08-19T10:30:00Z"
}
```

**Security Event Types:**

| Event | Triggered When |
|-------|---------------|
| `auth_failure` | API key validation fails |
| `authorization_failure` | Unauthorized access attempt |
| `rate_limit` | Tool rate limit exceeded |
| `validation_failure` | Invalid input parameters detected |
| `config_change` | `update_configuration` called |
| `circuit_breaker_state` | Circuit breaker opens or resets |

### 📊 **Compliance Impact**

**OWASP A09 (Logging Failures):**
- ✅ Log sanitization prevents data leakage (CWE-532)
- ✅ Security audit logging ensures audit trail (CWE-778)
- ✅ Proper log rotation with automatic disk management

## Rate Limiting

### ⚡ **Per-Tool Rate Limits**

Each MCP tool has an independent rate limiter to prevent abuse and protect API quotas:

| Tool | Rate Limit | Rationale |
|------|-----------|-----------|
| `assistant_chat` | 50 requests/minute | AI synthesis — highest cost |
| `assistant_context` | 100 requests/minute | Context retrieval — higher volume allowed |
| `assistant_strategic_multi_search_chat` | 10 requests/minute | Multi-search AI — most expensive |
| `assistant_strategic_multi_search_context` | 20 requests/minute | Multi-search context — bulk retrieval |

**Rate Limit Exceeded Response:**
```json
{
  "error": true,
  "success": false,
  "message": "Rate limit exceeded. Please wait before retrying.",
  "request_id": "abc-123"
}
```

Rate limit violations are automatically logged as `rate_limit` events in the security audit log.

## Circuit Breaker Protection

### 🔌 **Fast-Fail Protection**

The circuit breaker pattern (`src/resilience/circuit_breaker.py`) prevents cascading failures when the Pinecone API is unavailable:

- **Closed** (normal): Requests pass through to the API
- **Open** (failing): Fast-fail with immediate error response — no API calls made
- **Half-Open** (recovering): Test requests allowed to check if API has recovered

**Circuit Breaker Events** are logged to the security audit log as `circuit_breaker_state` events, enabling monitoring of API availability patterns.

## Request ID Tracking

### 🔍 **Correlation via RequestScope**

Every MCP tool invocation generates a unique `request_id` using `RequestScope`. This ID:
- Appears in all log messages for that request
- Is included in error responses for debugging
- Enables correlation between application logs and security audit logs
- Never contains sensitive data

```python
# Example log entries for a single request:
[abc-123] Processing assistant_context request
[abc-123] Query executed: top_k=5, snippet_size=2048
[abc-123] Returned 5 chunks, 8432 tokens
```

## Code Security Patterns

### ✅ **Secure Patterns**

**1. Input Validation via Pydantic:**
```python
from pydantic import BaseModel, field_validator

class AssistantContextRequest(BaseModel):
    query: str
    top_k: int = 5
    snippet_size: int = 2048

    @field_validator('top_k')
    def validate_top_k(cls, v):
        if not 1 <= v <= 64:
            raise ValueError("top_k must be between 1 and 64")
        return v
```

**2. API Key Format Validation:**
```python
# The config validates key format before use
if not api_key.startswith("pcsk_"):
    raise ValueError("Invalid Pinecone API key format")
```

**3. HTTPS Enforcement:**
```python
# HTTP only allowed for localhost in development
if not host.startswith("https://") and "localhost" not in host:
    raise ValueError("HTTPS is required for production environments")
```

**4. Request ID Tracking:**
```python
from src.util.request_scope import RequestScope

with RequestScope() as scope:
    request_id = scope.request_id
    logger.info(f"[{request_id}] Processing request")
```

### ❌ **Anti-Patterns to Avoid**

**1. Hardcoded Secrets:**
```python
# Never do this
API_KEY = "pcsk_example_hardcoded_key_never_do_this_12345"
```

**2. Secrets in Comments:**
```python
# Don't include real keys in comments
# My key is: pcsk_example_key_in_comment_bad_practice_67890
```

**3. Logging Secrets:**
```python
# Never log API keys
logger.info(f"Using API key: {api_key}")  # ❌
logger.info("Using configured API key")   # ✅ Safe
```

## Error Handling Security

### 🛡️ **Secure Error Responses**

The custom exception hierarchy (`src/exceptions.py`) ensures error responses never expose internal details:

```python
def format_error_response(message: str, status_code: int, request_id: str = None):
    """Format error without exposing sensitive data"""
    response = {
        "error": True,
        "success": False,
        "status_code": status_code,
        "message": message  # Never include API keys or internal paths
    }
    if request_id:
        response["request_id"] = request_id
    return response
```

### 🚨 **Information Disclosure Prevention**

**Sanitize error messages:**
```python
# ✅ Safe error message
"Authentication failed - check your Pinecone API key"

# ❌ Exposes internal information
f"Failed to authenticate with key {api_key} against {internal_url}"
```

Error messages at different verbosity levels are controlled by `DEBUG_LOGGING` — when disabled (default), stack traces are never returned to the MCP client.

## File and Repository Security

### 📁 **.gitignore Requirements**

```gitignore
# API Keys and Secrets
*api_key*
*API_KEY*
*.key
secrets.json
.env
.env.local
.env.production

# Configuration files with secrets
*local*.json
*_with_keys*
*_secrets*
config_real.json

# Session history (may contain sensitive data)
SESSION_HISTORY_*.md

# Audit reports (may contain sensitive findings)
audits/

# Claude Code integration
.claude/
```

### 🗂️ **Configuration Templates**

**Template files should use empty placeholders:**
```json
{
  "env": {
    "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io/assistant",
    "PINECONE_ASSISTANT_NAME": "your-assistant-name"
  },
  "documentation": "API key stored via DPAPI - not required in config file"
}
```

## Development Workflow Security

### 🔄 **Secure Development Process**

1. **Before Coding:**
   - Never commit real API keys
   - Use environment variables from day one
   - Set up `.gitignore` before first commit

2. **During Development:**
   - Use test keys for local development (e.g., `pcsk_test_key_for_testing`)
   - Implement proper error handling using custom exception hierarchy
   - Add request ID tracking for all log entries

3. **Before Committing:**
   - Run security scan: `uv run detect-secrets scan`
   - Verify no hardcoded secrets
   - Test with environment variables

4. **Before Publishing:**
   - Full security audit of codebase
   - Clean git history if needed
   - Verify all configuration templates

### 🧪 **Testing Security**

```python
# Security test example from tests/test_security.py
def test_no_hardcoded_secrets():
    """Ensure no hardcoded API keys in codebase"""
    import subprocess

    result = subprocess.run([
        'grep', '-rE', 'pcsk_[A-Za-z0-9_-]{20,}',
        '.', '--exclude-dir=.git', '--include=*.py'
    ], capture_output=True, text=True)

    assert result.returncode != 0, "Found hardcoded API key in codebase"
```

## Incident Response

### 🚨 **If API Key is Exposed**

**Immediate Actions (within 1 hour):**
1. **Invalidate the exposed key** at [Pinecone Console](https://app.pinecone.io/) → API Keys → Delete key
2. **Generate new API key** in the Pinecone Console
3. **Update stored key** by re-running `.\deploy\windows_setup.ps1` or `.\deploy\manage_assistant.ps1`
4. **Scan for unauthorized usage** in Pinecone API logs and billing dashboard

**Cleanup Actions (within 24 hours):**
1. **Remove from git history** if committed:
   ```bash
   # Use BFG Repo Cleaner
   # See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
   ```
2. **Review security audit logs** at `~/.pinecone_assistant/logs/security_audit.log` for suspicious activity
3. **Implement additional monitoring** if unauthorized usage detected
4. **Post-mortem** to identify how the key was exposed

### 📋 **Response Checklist**

- [ ] API key invalidated at Pinecone Console
- [ ] New key generated and deployed via DPAPI
- [ ] Git history cleaned (if needed)
- [ ] Security audit logs reviewed
- [ ] Monitoring implemented for new key
- [ ] Post-mortem completed
- [ ] Process improvements identified

## Monitoring and Auditing

### 📊 **Security Monitoring**

Review the security audit log regularly:

```bash
# View recent security events (Unix)
tail -f ~/.pinecone_assistant/logs/security_audit.log

# View recent security events (Windows PowerShell)
Get-Content "$env:USERPROFILE\.pinecone_assistant\logs\security_audit.log" -Wait
```

**Security events to watch for:**
```python
# Rate limit exceeded — possible abuse
{"event": "rate_limit", "tool": "assistant_chat", "timestamp": "..."}

# Authentication failures — possible key issues or unauthorized access
{"event": "auth_failure", "request_id": "...", "timestamp": "..."}

# Validation failures — possible malformed requests
{"event": "validation_failure", "details": "...", "timestamp": "..."}
```

### 🔍 **Regular Security Audits**

**Monthly Checklist:**
- [ ] Scan codebase for hardcoded secrets: `uv run detect-secrets scan`
- [ ] Review API key rotation schedule
- [ ] Check `.gitignore` effectiveness
- [ ] Verify test environment security
- [ ] Review error message exposure
- [ ] Check security audit logs for anomalies

## Tools and Automation

### 🔧 **Pre-commit Security Hooks**

The project's `.pre-commit-config.yaml` includes:

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: |
          (?x)^(
            audits/.*\.md|
            .*\.md|
            strategic-searches\.yaml
          )$

  # Additional hooks
  - id: trailing-whitespace
  - id: end-of-file-fixer
  - id: check-yaml
  - id: check-added-large-files
    args: ['--maxkb=1000']
  - id: check-json
  - id: check-merge-conflict
  - id: detect-private-key
```

**Install hooks (one-time setup):**
```bash
pip install pre-commit
pre-commit install
```

## Compliance and Best Practices

### 📋 **Security Compliance**

**OWASP Top 10 Alignment:**
- **A07:2021 – Identification and Authentication Failures**: DPAPI encryption, API key format validation, environment variable validation
- **A04:2021 – Insecure Design**: Secure-by-default patterns, HTTPS enforcement, circuit breaker
- **A05:2021 – Security Misconfiguration**: `.gitignore`, configuration templates, pre-commit hooks
- **A09:2021 – Security Logging and Monitoring Failures**: SecureFormatter (CWE-532, CWE-778), security audit log

**Windows Security:**
- **DPAPI**: Keys bound to Windows user account — cannot be decrypted by other users or moved to another machine
- **Credential Manager**: Windows-native secure storage with ACL protection

## Pinecone-Specific Considerations

### API Key Format
Pinecone Assistant API keys follow the format: `pcsk_*`. The codebase validates this format and rejects improperly formatted keys before any API calls are made.

### Host Configuration
Always use HTTPS for production hosts. The codebase enforces HTTPS for non-localhost connections. HTTP is only permitted for `localhost` during local development.

### Assistant Names
Assistant names must be at least 3 characters and contain only alphanumeric characters, hyphens, and underscores. This is validated by Pydantic models before any API calls.

### Data Privacy
Data sent to Pinecone for retrieval is subject to Pinecone's privacy policy and data retention terms. Do not input confidential, proprietary, or client-sensitive information without understanding these terms. See the disclaimer in [README.md](./README.md) for full details.

## Conclusion

Security is everyone's responsibility. By following these guidelines, we ensure that the Pinecone Assistant MCP Server remains secure and protects user data and API credentials. Regular review and updates of these guidelines help maintain security posture as the project evolves.

For questions about security practices or to report security issues, contact the project maintainers immediately.

📖 **See [SECURITY_SCANNING.md](./SECURITY_SCANNING.md)** for automated scanning setup and prompt injection detection details.
