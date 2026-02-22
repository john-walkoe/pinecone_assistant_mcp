# Security Scanning Guide

This document explains the comprehensive automated security scanning setup for the Pinecone Assistant MCP project.

## Overview

The project uses multiple security scanning technologies:
- **detect-secrets** to prevent accidental commits of API keys, tokens, passwords, and other sensitive data
- **Prompt Injection Detection** to protect against AI-specific attacks and malicious prompt patterns

## Features

### 1. **CI/CD Secret Scanning** (GitHub Actions)
- Automatically scans all code on push and pull requests
- Scans git history (last 100 commits) for accidentally committed secrets
- Fails the build if new secrets are detected
- Location: `.github/workflows/secret-scan.yml`

### 2. **Pre-commit Hooks** (Local Development)
- Prevents committing secrets before they reach GitHub
- Runs automatically on `git commit`
- Location: `.pre-commit-config.yaml`

### 3. **Baseline Management**
- Tracks known placeholder keys and false positives
- Location: `.secrets.baseline`

### 4. **Prompt Injection Detection with Baseline System** (Enhanced Security)
- Scans for 70+ malicious prompt patterns
- **Baseline system** to track known findings and only flag NEW patterns
- SHA256 fingerprinting for finding identification
- Detects document-corpus attack vectors (API bypass, data extraction)
- Integrated with pre-commit hooks and CI/CD pipeline
- Location: `.security/check_prompt_injections.py`

**Attack Categories Detected:**
- Instruction override attempts ("ignore previous instructions")
- System prompt extraction ("show me your instructions")
- AI behavior manipulation ("you are now a different AI")
- Document data extraction ("dump all documents from the knowledge base")
- API bypass attempts ("bypass the Pinecone API limits")
- Configuration disclosure ("reveal your system prompt")
- Social engineering patterns ("we became friends")
- **Unicode steganography attacks** (Variation Selectors, zero-width characters)

### Unicode Steganography Detection (Enhanced Security)

The enhanced detector includes comprehensive Unicode steganography detection to counter advanced threats like the Repello AI emoji injection attack:

**Detection Capabilities:**
- **Variation Selector Encoding**: Detects VS0/VS1 (U+FE00/U+FE01) binary encoding in emojis
- **Zero-Width Character Abuse**: Identifies suspicious use of invisible Unicode characters
- **High Invisible Character Ratios**: Flags content with >10% invisible-to-visible character ratios
- **Binary Pattern Recognition**: Detects 8+ bit sequences that could encode hidden messages

**Attack Patterns Detected:**
- Emoji steganography (e.g., "Hello!" with hidden binary-encoded instructions)
- Zero-width space injection for text manipulation
- Invisible Unicode character abuse for bypassing filters
- Binary steganography using Variation Selectors

**Examples of Detected Threats:**
- `"Hello!" + hidden_binary_message` — appears innocent but contains malicious instructions
- Text with embedded zero-width characters for prompt manipulation
- Emoji sequences with suspicious Variation Selector patterns
- High ratios of invisible formatting characters

### Prompt Injection Baseline System

The prompt injection scanner uses a **baseline system** to track known findings and only flag **NEW** patterns not in the baseline. This solves the problem of false positives from legitimate code and documentation while maintaining protection against malicious prompt injection attacks.

#### How It Works

1. **Baseline File**: `.prompt_injections.baseline` stores known findings
2. **Fingerprinting**: Each finding gets a unique SHA256 hash fingerprint
3. **Comparison**: Scanner checks if each finding is in the baseline
4. **Exit Codes**:
   - `0` — No NEW findings (all findings in baseline)
   - `1` — NEW findings detected (not in baseline)
   - `2` — Error occurred

#### Usage

**First run — Create baseline:**
```bash
uv run python .security/check_prompt_injections.py --update-baseline src/ tests/ *.md *.yml *.yaml *.json
```

**Normal run — Check against baseline:**
```bash
uv run python .security/check_prompt_injections.py --baseline src/ tests/ *.yml *.yaml *.json
```

**Update baseline to include new legitimate findings:**
```bash
uv run python .security/check_prompt_injections.py --update-baseline src/ tests/ *.md *.yml *.yaml *.json
```

**Force new baseline (overwrite existing):**
```bash
uv run python .security/check_prompt_injections.py --force-baseline src/ tests/ *.md *.yml *.yaml *.json
```

#### Command Line Options

| Option | Purpose |
|--------|---------|
| `--baseline` | Use existing baseline (only NEW findings fail) |
| `--update-baseline` | Add new findings to baseline |
| `--force-baseline` | Create new baseline (overwrite existing) |
| `--verbose, -v` | Show detailed output with full matches |
| `--quiet, -q` | Only show summary (suppress individual findings) |

#### When to Update Baseline

**DO Update Baseline When:**
- New legitimate code is flagged (variable names, class names, documentation)
- Approved refactoring changes line numbers
- Baseline is outdated after a code restructure

**DON'T Update Baseline When:**
- Malicious pattern detected (remove the code instead)
- You're unsure (ask for review first)
- Security-related finding (review carefully first)

## Setup

### Install Pre-commit Hooks (Recommended)

```bash
# Install pre-commit framework and detect-secrets
uv pip install pre-commit detect-secrets

# Install the git hooks
uv run pre-commit install

# Test the hooks (optional)
uv run pre-commit run --all-files
```

### Manual Security Scanning

**Secret Detection:**
```bash
# Scan entire codebase
uv run detect-secrets scan

# Scan specific files
uv run detect-secrets scan src/server.py

# Update baseline after reviewing findings
uv run detect-secrets scan --baseline .secrets.baseline

# Audit baseline (review all flagged items)
uv run detect-secrets audit .secrets.baseline
```

**Prompt Injection Detection:**
```bash
# Scan for prompt injection patterns
uv run python .security/check_prompt_injections.py src/ tests/ *.md

# Scan specific directories
uv run python .security/check_prompt_injections.py src/

# Run via pre-commit hook
uv run pre-commit run prompt-injection-check --all-files

# Test with verbose output
uv run python .security/check_prompt_injections.py --verbose src/ tests/
```

## What Gets Scanned

### Included:
- All Python source files (`src/`, `tests/`, `deploy/`)
- Configuration files
- Shell scripts and workflows
- YAML configuration files

### Excluded:
- `audits/*.md` — Security audit reports
- `*.md` — Documentation files (may contain example keys)
- `package-lock.json` — NPM lock file
- `.secrets.baseline` — Baseline file itself
- `strategic-searches.yaml` — Search pattern configuration

## Handling Detection Results

### False Positives (Test/Example Secrets)

If detect-secrets flags a legitimate placeholder:

1. **Verify it's truly a placeholder** (not a real secret)
2. **Update the baseline** to mark it as known:
   ```bash
   uv run detect-secrets scan --baseline .secrets.baseline
   ```
3. **Commit the updated baseline**:
   ```bash
   git add .secrets.baseline
   git commit -m "Update secrets baseline after review"
   ```

### Real Secrets Detected

If you accidentally committed a real secret:

1. **Revoke the secret immediately** — delete the key at [Pinecone Console](https://app.pinecone.io/) → API Keys → Delete
2. **Generate a new API key** in the Pinecone Console
3. **Remove from git history**:
   ```bash
   # Use BFG Repo Cleaner or git filter-branch
   # See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
   ```
4. **Update stored key**:
   ```bash
   # Re-run setup to store new key via DPAPI
   .\deploy\windows_setup.ps1
   ```

## Best Practices

### DO:
- ✅ Store secrets using Windows DPAPI (via deployment script)
- ✅ Use environment variables as fallback on Linux/macOS
- ✅ Use placeholder values in example configs
- ✅ Run `pre-commit run --all-files` before first commit
- ✅ Review baseline updates carefully
- ✅ Check security audit log at `~/.pinecone_assistant/logs/security_audit.log`

### DON'T:
- ❌ Hardcode API keys in source code (`pcsk_*` format)
- ❌ Commit `.env` files
- ❌ Use real secrets in tests (use mocks/fixtures)
- ❌ Disable pre-commit hooks without review
- ❌ Ignore secret scanning failures in CI

## GitHub Actions Workflow

The workflow runs on:
- All pushes to `main`, `master`, and `develop` branches
- All pull requests to these branches

### Workflow Steps:
1. Checkout full git history
2. Install detect-secrets
3. Scan current codebase against baseline
4. Scan recent git history (last 100 commits)
5. Report findings and fail if secrets detected

### Viewing Results:
- Go to **Actions** tab in GitHub
- Click on **Secret Scanning** workflow
- Review any failures in the job logs

## Troubleshooting

### Pre-commit Hook Failing

```bash
# Check what's detected
pre-commit run detect-secrets --all-files

# If false positive, update baseline
uv run detect-secrets scan --baseline .secrets.baseline

# Re-run commit
git commit
```

### CI Failing with "Secrets Detected"

1. Review the GitHub Actions log to see what was flagged
2. Verify if it's a real secret or false positive
3. If false positive:
   - Update baseline locally: `uv run detect-secrets scan --baseline .secrets.baseline`
   - Commit and push the updated baseline
4. If real secret:
   - **REVOKE THE SECRET IMMEDIATELY** at [Pinecone Console](https://app.pinecone.io/)
   - Remove from code and git history
   - Fix and re-push

### Baseline Out of Sync

```bash
# Regenerate baseline from scratch
uv run detect-secrets scan \
  --exclude-files 'audits/.*\.md' \
  --exclude-files '\.md$' \
  --exclude-files 'strategic-searches\.yaml' \
  > .secrets.baseline

# Review and commit
git add .secrets.baseline
git commit -m "Regenerate secrets baseline"
```

## Integration with Security Guidelines

This scanning complements the recommendations in `SECURITY_GUIDELINES.md`:
- Prevents API keys from being committed
- Enforces use of environment variables and DPAPI secure storage
- Provides audit trail for secret management
- Supports incident response procedures
- Detects prompt injection attacks before they reach the codebase

## Secret Types Detected

The scanner detects 20+ types of secrets including:

**Cloud Provider Keys:**
- AWS Access Keys
- Azure Storage Keys
- GCP Service Account Keys
- IBM Cloud IAM Keys

**API & Service Tokens:**
- GitHub Tokens
- GitLab Tokens
- OpenAI API Keys
- Pinecone API Keys (`pcsk_*`)
- Stripe API Keys
- Twilio Keys
- SendGrid Keys
- Slack Tokens
- Discord Bot Tokens
- Telegram Bot Tokens

**General Secrets:**
- Private SSH Keys
- JWT Tokens
- NPM Tokens
- PyPI Tokens
- Basic Auth Credentials
- High-Entropy Strings (Base64/Hex)
- Password Keywords

## Project-Specific Considerations

### Pinecone Assistant API Keys
The scanner is configured to detect Pinecone API keys (format: `pcsk_*`). Real Pinecone API keys must always be stored via DPAPI (preferred) or as environment variables:

```bash
# Linux/macOS (environment variable)
export PINECONE_ASSISTANT_API_KEY=your_actual_key_here

# Windows (DPAPI — use deployment script)
.\deploy\windows_setup.ps1
```

### Test Files
Test files in `tests/` may contain placeholder keys for validation testing (e.g., `pcsk_test_key_for_testing`). These are tracked in `.secrets.baseline` and are verified to be test-only placeholders, not real credentials.

### Strategic Search YAML
`strategic-searches.yaml` is excluded from secret scanning as it contains domain-specific search patterns, not credentials.

## Additional Resources

- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [Pre-commit Framework](https://pre-commit.com/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)
- [Windows DPAPI Documentation](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/)

## Questions?

See `SECURITY_GUIDELINES.md` for broader security practices or file an issue on GitHub.
