# Pinecone Assistant MCP

A **generic** Model Context Protocol (MCP) server for conversational AI document research using the Pinecone Assistant API. This architecture is **fully customizable** for any document corpus and provides your LLM MCP access to fully customizable knowledge base and Retrieval-augmented generation (RAG) benefits without embedding complications by using Pinecone Assistants.

**Reference Implementation:** USPTO patent examination documents (MPEP, Subsequent Publications, Examination Guidelines and Examiner Training Materials) are included as an example use case with 11 pre-configured search domains organized by legal issue areas.

[![Platform Support](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![API](https://img.shields.io/badge/API-Pinecone%20Assistant-green.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[📊 Pinecone MCP Comparison](PINECONE_MCP_COMPARISON.md)** | Compare all 5 Pinecone MCP implementations (Official Assistant, Official Vector DB, this repo, pinecone_rag_mcp, pinecone_diff_rag_mcp) |
| **[📥 Installation Guide](INSTALL.md)** | Complete cross-platform setup with automated scripts |
| **[🔑 API Key Guide](PINECONE_KEY_GUIDE.md)** | Step-by-step guide to obtaining and securing your Pinecone API key |
| **[📖 Usage Examples](USAGE_EXAMPLES.md)** | Function examples, workflows, and integration patterns |
| **[🗒️ Prompt Templates](PROMPTS.md)** | MCP prompt templates for guided research workflows |
| **[🔧 Customization Guide](CUSTOMIZATION.md)** | Adapting to non-USPTO document domains |
| **[🔒 Security Guidelines](SECURITY_GUIDELINES.md)** | Security best practices, DPAPI encryption, secure logging, and incident response |
| **[🛡️ Security Scanning](SECURITY_SCANNING.md)** | Automated secret scanning and prompt injection detection setup |
| **[🎯 Claude Skills](skills/README.md)** | Installation and usage guide for the three included Claude skills |
| **[🧪 Test Suite](tests/README.md)** | Comprehensive test documentation and guidelines |
| **[⚖️ License](LICENSE)** | MIT License terms and conditions |

### Claude Skills

Three skills are included in `skills/` for guided research workflows in Claude Code and Claude.ai:

| Skill | Audience | Description |
|-------|----------|-------------|
| [`pinecone-assistant`](skills/pinecone-assistant/SKILL.md) | Any corpus | Generic RAG workflows — tool selection, token optimization, multi-assistant setup |
| [`pinecone-assistant-uspto`](skills/pinecone-assistant-uspto/SKILL.md) | USPTO / MPEP corpus | Domain selection, office action response workflows, multi-MCP integration |
| [`pinecone-assistant-paid-plan`](skills/pinecone-assistant-paid-plan/SKILL.md) | Paid plan / agentic | `assistant_chat` delegation patterns, `context_options` tuning, agentic chaining |

## ⚡Quick Start

**Run PowerShell as Administrator**, then:

```powershell
# Navigate to your user profile
cd $env:USERPROFILE

# If git is installed:
git clone https://github.com/john-walkoe/pinecone_assistant_mcp.git
cd pinecone_assistant_mcp

# If git is NOT installed:
# Download and extract the repository to C:\Users\YOUR_USERNAME\pinecone_assistant_mcp
# Then navigate to the folder:
# cd C:\Users\YOUR_USERNAME\pinecone_assistant_mcp

# The script detects if uv is installed and if it is not it will install uv - https://docs.astral.sh/uv

# Run setup script (sets execution policy for this session only):
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process
.\deploy\windows_setup.ps1

# Close Powershell Window.
# If choose option to "configure Claude Desktop integration" during the script then restart Claude Desktop
```

The setup script will:
- Install dependencies (uv package manager, Python)

- Prompt for your Pinecone API key  

- Create or connect to a Pinecone Assistant

- Upload USPTO documents or your custom files

- Provide 2 options to Configure Claude Desktop integration
  - Secure Python DPAPI (recommended) - API key encrypted with Windows DPAPI; stored in `~/.pinecone_api_key` (Credential Manager target: `pinecone_API_KEY`). The JSON config contains **no API key and no `INTERNAL_AUTH_SECRET`** — decryption is self-contained (entropy embedded in bytes 0–31 of the key file)
  
    ![DPAPI API Keys in Windows Credential Manager](documentation_photos\Pinecone_DPAPI.jpg)
  
  - Traditional - More reliable but API key stored in config file


**After setup**: Restart Claude Desktop to load the MCP server.

### Claude Desktop Configuration - Manual installs

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "PINECONE_API_KEY": "pcsk_YOUR_KEY",
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o",
        "DEFAULT_TEMPERATURE": "0.2"
      }
    }
  }
}
```

**For detailed installation, manual setup, and troubleshooting**, see **[INSTALL.md](./INSTALL.md)**

## 🎯 Key Benefits

- **🔧 Fully Customizable**: Adapt to any document domain by replacing documents and YAML search patterns
- **🔐 Secure API Storage**: Windows DPAPI encryption eliminates plain text API keys in configuration files
- **📚 Domain-Agnostic**: Architecture works for legal, medical, technical, financial, or any document corpus
- **🤖 Advanced Models**: Access to GPT-4o, GPT-5, Claude-4.5-Sonnet, Gemini-2.5-Pro for responses
- **🔗 Rich Citations**: Text highlights with precise source attribution and page numbers
- **💬 Conversation Context**: Multi-turn discussions with full conversation memory
- **🔍 Strategic Search**: Configurable research workflows via YAML patterns (no code changes needed)
- **🎨 Customizable System Prompts**: Domain-specific optimization via template files (USPTO/generic)
- **🔄 Assistant Switching**: Check configuration with `get_configuration_status` and switch between assistants mid-conversation with `update_configuration`
- **📝 MCP Prompts**: Four corpus-neutral prompt templates (`deep_research`, `quick_lookup`, `comparative_research`, `delegated_research`) accessible from the Claude prompt menu
- **🎯 Claude Skills**: Three included skills for guided research workflows — generic, USPTO-specific, and paid-plan delegation
- **🛠️ Management Tool**: Standalone script `manage_assistant.ps1` for easy assistant creation, configuration, and maintenance
- **⚡ Simple Deployment**: Automated setup script handles document upload and configuration
- **📖 Example Corpus**: USPTO MPEP, Subsequent Publications (to December 2025), Examination Guidelines and Examiner Training Materials documents included as reference and designed to work with the author's USPTO MCPs

## 📊 Available Functions

### 🛠️ MCP Tools

| Function (Display Name) | Purpose | Requirements |
|------------------------|---------|--------------|
| `assistant_context` (Assistant context) | Retrieve raw document chunks/snippets without AI processing | PINECONE_ASSISTANT_API_KEY |
| `assistant_strategic_multi_search_context` (Assistant strategic multi search context) | Execute strategic research patterns returning raw document chunks | PINECONE_ASSISTANT_API_KEY |
| `assistant_strategic_multi_search_chat` (Assistant strategic multi search chat) | Execute strategic research patterns with AI-generated responses | PINECONE_ASSISTANT_API_KEY |
| `assistant_chat` (Assistant chat) | Direct conversation with Pinecone Assistant for AI-powered research | PINECONE_ASSISTANT_API_KEY |
| `get_configuration_status` (Get configuration status) | Check current assistant configuration (name, host, model) | PINECONE_ASSISTANT_API_KEY |
| `update_configuration` (Update configuration) | Switch between different Pinecone Assistants or change settings mid-conversation | PINECONE_ASSISTANT_API_KEY |
| `evaluate_answer` (Evaluate answer) | Evaluate AI answer quality against ground truth (alignment/correctness/completeness scores) | PINECONE_ASSISTANT_API_KEY + **Paid plan required** |

#### Token Usage Optimization

**Pinecone Assistant API Free Starter Tier Limits (Starter Plan):**

⚠️ **IMPORTANT: These token limits are LIFETIME limits per project, NOT monthly limits:**
- **Context tokens**: 500K total per project (used by context retrieval tools)
- **Input tokens**: 1.5M total per project (used by AI chat tools)
- **Output tokens**: 200K total per project (generated by AI responses)
- **File Storage:** 1GB per project, 100 Files per assistant, file size 10MB (.docx, .json, .md, .txt, .pdf) 

**Unlike Free Tier Limits on traditional Pinecone's database RUs and WUs, these Pinecone Assistant token quotas do NOT reset monthly.** Once exhausted, you must either:

1. **Upgrade to a paid plan** (Standard: $50/month minimum, Enterprise: $500/month minimum) - **Recommended for production use**
2. **Delete and recreate your project** to reset limits - **For extended testing only**

**⚠️ Paid Plan Costs:**

- **Standard Plan**: $50/month minimum (even if usage is less)
  - Hourly rate: $0.05/hour per assistant (regardless of activity)
  - Input tokens: $8/million, Output tokens: $15/million, Context tokens: $5/million
  - Storage: $3/GB per month
- **Enterprise Plan**: $500/month minimum with custom pricing

**Reference:** [Pinecone Assistant Pricing & Limits](https://docs.pinecone.io/guides/assistant/pricing-and-limits)

**Tools listed in recommended usage order**

### 🗒️ MCP Prompts

Four corpus-neutral prompt templates accessible from the Claude prompt menu. Each prompt generates a structured workflow with pre-filled tool calls:

| Prompt | Parameters | Token Tier | Use When |
|--------|-----------|-----------|---------|
| `deep_research` | `topic`, `domain?` | Context only | Thorough multi-angle coverage via strategic multi-search |
| `quick_lookup` | `topic` | Context only | Fast single-fact retrieval (one tool call) |
| `comparative_research` | `topic_a`, `topic_b` | Context only | Side-by-side comparison of two topics |
| `delegated_research` | `research_question`, `model?`, `prior_context?` | Context + LLM | Delegate synthesis to Pinecone AI (paid plan / agentic) |

**Token tiers:**
- **Context only** — uses the 500K context token pool; no AI synthesis cost
- **Context + LLM** — uses both context tokens and LLM input/output tokens (`assistant_chat` delegation)

### `assistant_context`
**Retrieve raw document chunks/snippets without AI processing.**

**Token Cost**: ~5-10K context tokens per query (Free Plan - uses 500K Context tokens/lifetime allocation)
**Recommended for**: 90% of queries

**Features:**
- Returns actual document chunks that the Assistant would use
- Zero AI processing costs - no input/output tokens consumed
- Configurable chunk size (512-8192 tokens) and quantity (1-64, default: 5)
- Direct source references and relevancy scores
- Perfect for feeding into your own analysis
- Multimodal support: retrieve image context from PDFs (query-only)
- Multi-turn context via messages input (alternative to query)

**Note**: Either `query` OR `messages` is required (not both). The `multimodal` and `include_binary_content` parameters are only available with `query` input and are ignored when using `messages`.

**If on free plan Try this first** before escalating to AI-powered tools.

### `assistant_strategic_multi_search_context`
**Multi searches **using user predefined domains search patterns - returns raw chunks so the host LLM can analyze

**Token Cost**: ~10-15K context tokens per query (Free Plan - uses 500K Context tokens/lifetime allocation)
**Recommended for**: Comprehensive multi-topic research without AI synthesis

**Features:**
- Combines systematic coverage of strategic search with raw document access
- Returns raw text organized by search patterns
- Configurable chunk size per search pattern
- Zero AI processing costs - no input/output tokens consumed
- Dynamically adapts to domains defined in strategic-searches.yaml

### `assistant_chat`

**Direct conversation with Pinecone Assistant for AI-powered research.**

**Token Cost**: ⚠️ ~30K+ input tokens + ~2-5K output tokens per query (Free Plan - uses Chat input/output allocations - Free tier limited to 1.5M input/200K lifetime allocation)
**Recommended for**: Complex questions requiring AI synthesis (try assistant_context first)

**Features:**

- Multi-turn conversation support (⚠️ use sparingly - see conversation guidance below)
- Rich citations with text highlights from source documents
- Model selection (GPT-4o, GPT-5, Claude Sonnet 4.5, Gemini Pro 2.5)
- Temperature control for response creativity

**Try this for a built-in multi-agent workflow** - uses a multi agent workflow.  For instance when using a high context host LLM for synthesis call this tool and you can get the reasoning or specialized system prompt of another model to do the context retrieval and analysis.  (That other model is either set in the `model` field of the tool use or if not set in tool use then will default to the `PINECONE_ASSISTANT_MODEL` environmental variable) 

**⚠️ Multi-turn Conversation Warning**: The API is stateless. Only include conversation history when your new question explicitly references prior context (pronouns like "that", "this", references like "as mentioned"). Most questions should be stateless single-message queries. Including unnecessary history can waste significant tokens!

### `assistant_strategic_multi_search_chat`
**Execute strategic research patterns with AI-generated responses.**

**Token Cost**: ⚠️ ~30K input tokens + ~5K output tokens per query (Free Plan - uses Chat input/output allocations - Free tier limited to 1.5M input/200K lifetime allocation)
**Recommended for**: When you need AI to synthesize information across searches

**Features:**

- Uses pre-defined search patterns with keyword substitution

- Executes multiple targeted AI chat searches

- Aggregates AI-synthesized results with preserved citations

- Best when you need expert analysis, not just documents


**Same AI usage as the `assistant_chat` tool** but paring it with with multi searches using user predefined domains search patterns.

### `get_configuration_status`
**Check current Pinecone Assistant configuration.**

- Verify which assistant is currently active before switching
- Confirm `update_configuration` changes took effect

- Returns current assistant name, host URL, and default model

### `update_configuration` 🔄
**Switch between different Pinecone Assistants or change settings mid-conversation.**

**Use Cases:**
- Switch between specialized knowledge bases (Free Plan: you can have up to 5 assistants)
- Change default AI model without restarting Claude Desktop
- Leverage multiple document corpora in a single research session

**Features:**
- Auto-detection of assistant host URL
- No restart required - immediate effect
- Revert by restarting Claude Desktop
- Detailed change reporting

**Example:**
```json
{
  "tool": "update_configuration",
  "arguments": {
    "assistant_name": "case-law-assistant",
    "model": "claude-4-5-sonnet"
  }
}
```

See **[Multi-Assistant Workflows](USAGE_EXAMPLES.md#multi-assistant-workflows)** for detailed examples.

### `evaluate_answer` 📊 *(Paid plan required)*
**Evaluate AI-generated answer quality against a ground truth.**

**⚠️ Requires Pinecone Standard (paid) plan.** Returns an error on the free tier.

**Token Cost**: ~5-10K evaluation tokens per call (billed to Pinecone paid plan).

**Rate Limit**: 20 requests/minute.

**Features:**
- Three quality scores (0.0–1.0): correctness (precision), completeness (recall), alignment (harmonic mean)
- Per-fact entailment reasoning: each ground-truth fact classified as entailed, contradicted, or neutral
- Token usage reporting

**Use Cases:**
- Benchmarking assistant responses against known-correct answers
- Regression testing after prompt or document changes
- Validating that retrieved context yields accurate answers

**Example:**
```json
{
  "tool": "evaluate_answer",
  "arguments": {
    "question": "What is the Alice two-step test?",
    "answer": "The Alice test has two steps: step 1 determines...",
    "ground_truth_answer": "Alice Corp v. CLS Bank established a two-part test..."
  }
}
```

## USPTO Example Documents (Included)

The default `combined_documents.zip` contains USPTO patent examination documents:

- [**Manual of Patent Examining Procedure (MPEP)** - 9th Edition, Revision 01.2024](https://www.uspto.gov/web/offices/pac/mpep/) - Combined_MPEP_9th_Edition_Part1-4.md (Split into 4 parts so could be uploaded to pinecone assistant's free tier)

- [**Manual of Patent Examining Procedure (MPEP)** - Appendix L - Consolidated Patent Laws - July 2025 Update](https://www.uspto.gov/web/offices/pac/mpep/consolidated_laws.pdf) - mpep-9015-appx-l-July-2025.md

- [**Manual of Patent Examining Procedure (MPEP)** - Appendix R - Consolidated Patent Rules - July 2025 Update](https://www.uspto.gov/web/offices/pac/mpep/consolidated_rules.pdf) - mpep-9020-appx-r-July-2025.md

- [**Subsequent Publications (After January 31, 2024) July 2025 Update**](https://www.uspto.gov/web/offices/pac/mpep/subsequent-publications.pdf) & [**Patent related notices Jan 2024 - December 29, 2025**](https://www.uspto.gov/patents/laws/patent-related-notices/patent-related-notices-2025) - Combined_MPEP_Updates.md

- **[USPTO Examination Guidelines and Training Materials](https://www.uspto.gov/patents/laws/examination-policy/examination-guidance-and-training-materials)** - Combined_Training_Materials.md

**Document Processing:**

- All documents converted from PDF or PPTX to Markdown using [Docling](https://github.com/DS4SD/docling)
- Optimized for text-based RAG retrieval
- Pre-formatted for semantic search applications

**Supported File Types:**
Pinecone Assistant supports the following file types (all supported by upload script):
- **DOCX (.docx)** - Microsoft Word documents
- **JSON (.json)** - Structured data files  
- **Markdown (.md)** - Formatted text documents
- **PDF (.pdf)** - Portable Document Format files
- **Text (.txt)** - Plain text files

**File Size Limits:**
- **Free Plan**: 10MB for all file types
- **Standard/Enterprise**: 10MB (.md/.txt/.docx/.json), 100MB (.pdf)

**Copyright Status:**

- ⚠️ **U.S. Users**: All documents are U.S. Government works and are in the **public domain** within the United States under 17 U.S.C. § 105
- 🌍 **International Users**: Copyright status may vary by jurisdiction. Users outside the United States should verify copyright status in their country before use
- 📚 **Original Source**: All documents are official USPTO publications available at [uspto.gov](https://www.uspto.gov/)

## 🔧 Customizing for Your Own Documents

To adapt this MCP for your own document corpus:

1. **Replace documents** in `deploy/combined_documents/`:
   - Option A: Place your document files (DOCX, JSON, MD, PDF, TXT) directly in the directory
   - Option B: Create `combined_documents.zip` with your documents
   - Option C: Create `combined_documents.zip` with your documents and place additional document files (DOCX, JSON, MD, PDF, TXT) directly in the directory
   
2. **Update search patterns** in `strategic-searches.yaml`:
   - Replace USPTO domains with your domain structure
   - Customize search queries for your content

3. **Run setup script:**
   ```powershell
   .\deploy\windows_setup.ps1
   ```
   The script will prompt for your API key and assistant name.

   **Alternative**: Use the management script for more control:
   ```powershell
   .\deploy\manage_assistant.ps1
   ```

**Customizable System Prompts:** The MCP includes USPTO-specific system prompts for the  that use IRAC methodology for legal analysis, when using `assistant_strategic_multi_search_chat` or `assistant_chat`. For other domains, edit the generic system prompt template to optimize assistant responses for medical research, financial analysis, technical documentation, or any other field.

See **[CUSTOMIZATION.md](./CUSTOMIZATION.md)** for detailed examples (medical, financial, technical documentation)

## 🔄 Multi-Assistant Support

**Switch between up to 5 specialized assistants (free tier)** mid-conversation using `get_configuration_status` and `update_configuration`.

**Benefits:**
- Single conversation spans multiple knowledge bases
- 10 file limit per assistant → 50 files total across 5 assistants
- Specialized search patterns per domain
- No restart required - immediate switching
- Verify current configuration before switching

**Example workflow**: Check config → Start with MPEP → Switch to case lawbooks (not included) → Verify switch → All in one conversation.

See **[Multi-Assistant Workflows](USAGE_EXAMPLES.md#multi-assistant-workflows)** for detailed examples and domain-specific setups.

## 🛠️ Assistant Management Tool

**Standalone script for managing Pinecone Assistants** without running full MCP setup.

### Usage

```powershell
.\deploy\manage_assistant.ps1
```

### Features

**Menu-Driven Interface:**
1. **Create new assistant** - Set up a new assistant instance
2. **List all assistants** - View all assistants in your account
3. **Get assistant details** - Inspect configuration and metadata
4. **Upload documents** - Add/update documents in an assistant
5. **Update system prompt** - Change assistant instructions
6. **Delete assistant** - Remove assistant (with confirmation)
7. **Exit** - Close the tool

### 🔄 Project Management for Free Tier

**For Starter Plan users who need to reset token limits:**

The Starter Plan has **lifetime token limits per project** (not monthly). When you exhaust these limits, you can delete and recreate your project to get fresh limits. However, **Starter Plan allows only 1 project at a time**, so you must delete the old project first.

**⚠️ Important Considerations:**
- Deleting a project **permanently deletes ALL resources** in that project:
  - All assistants and their documents
  - All vector databases (indexes) and their data
  - All backups and collections
  - All project configuration
- **If you have production vector databases in this project, DO NOT delete it!**
- You will need to **re-upload all documents** after creating the new project
- This is intended for **extended testing only**
- **For production use, consider paid plans** but be aware of costs (Standard: $50/month minimum + hourly + usage charges)

**Automated Workflow (NEW - Recommended):**
```powershell
# Use the new project management tool
.\deploy\manage_project.ps1
```
This script will guide you through:
- Listing your projects and assistants
- Deleting all assistants in the project
- Providing instructions for project deletion in Pinecone Console
- Reminders about recreating your setup

**Manual Workflow:**
1. Note your current project configuration (assistant names, documents, system prompts)
2. Use `manage_assistant.ps1` → Option 6 to delete all assistants in your project
3. Delete any vector databases (indexes) in the project via [Pinecone Console](https://app.pinecone.io/)
4. Delete your project: Projects → Delete your project
5. Create a new project in the Pinecone Console
6. Run `.\deploy\windows_setup.ps1` to recreate assistants and upload documents
7. Reconfigure Claude Desktop with the new assistant details

**Alternative for testing:** Consider using `assistant_context` and `assistant_strategic_multi_search_context` tools which use context tokens (500K limit) instead of input/output tokens, allowing more queries before hitting limits.

## 💻 Usage Examples & Integration Workflows

For comprehensive usage examples, including:
- **AI-Powered Research** patterns
- **Raw Document Retrieval** optimization
- **Strategic search patterns** and multi-tool workflows
- **Cost optimization strategies**
- **Multi-Assistant workflows** for complex research

See the detailed [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) documentation.

## 🔗 Cross-MCP Integration

This MCP is designed to work seamlessly with other USPTO MCPs as a knowledge base for comprehensive patent lifecycle analysis:

### Related USPTO MCP Servers

| MCP Server | Purpose | GitHub Repository |
|------------|---------|-------------------|
| **USPTO Patent File Wrapper (PFW)** | Prosecution history & documents | [uspto_pfw_mcp](https://github.com/john-walkoe/uspto_pfw_mcp.git) |
| **USPTO Final Petition Decisions (FPD)** | Petition decisions during prosecution | [uspto_fpd_mcp](https://github.com/john-walkoe/uspto_fpd_mcp.git) |
| **USPTO Patent Trial and Appeal Board (PTAB)** | Post-grant challenges | [uspto_ptab_mcp](https://github.com/john-walkoe/uspto_ptab_mcp.git) |
| **Pinecone Assistant MCP** | Patent law knowledge base (MPEP, examination guidance) | [pinecone_assistant_mcp](https://github.com/john-walkoe/pinecone_assistant_mcp.git) |

### Integration Overview

The **Pinecone Assistant MCP** provides the knowledge base foundation for patent research, offering MPEP guidance and examination standards. When combined with the other MCPs, it enables:

- **Assistant + PFW**: Research MPEP guidance before extracting expensive prosecution documents
- **Assistant + FPD**: Understand petition standards and procedures before analysis
- **Assistant + PTAB**: Research board precedent and standards before detailed analysis
- **PFW + FPD + PTAB + Assistant**: Complete patent lifecycle analysis with knowledge base support

For detailed integration workflows, cross-referencing examples, and complete use cases, see [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md#cross-mcp-integration-workflows).

## Architecture

This is a **domain-agnostic MCP server** that adapts to your document corpus with **production-grade resilience**:

### Core Components
- **MCP Server** (`src/server.py`): Main MCP tool implementation with dynamic domain loading
- **API Layer** (`src/api/`):
  - `assistant_client.py`: HTTP client for Pinecone Assistant API with retry logic
- **Services Layer** (`src/services/`):
  - `strategic_search.py`: YAML-driven multi-search orchestration
  - `strategic_context.py`: Context-only search implementation
- **Configuration** (`src/config/`):
  - `config.py`: Environment-based secure configuration
  - `secure_storage.py`: Windows DPAPI secure API key storage
- **Data Models** (`src/models/models.py`): Pydantic models for validation
- **Search Patterns** (`strategic-searches.yaml`): **Fully customizable** domain definitions (no code changes needed)
- **Document Deployment** (`deploy/`): Automated document upload and configuration scripts

### Resilience & Fault Tolerance (`src/resilience/`)
- **Retry Logic** (`retry_utils.py`): Exponential backoff with jitter (3 attempts, 1s-60s delays)
- **Circuit Breaker** (`circuit_breaker.py`): Fast-fail protection against cascading failures
- **Response Caching** (`cache.py`): In-memory caching (Context: 10min TTL, Chat: 3min TTL)
- **Bulkhead Pattern** (`bulkhead.py`): Resource isolation via concurrency limits
- **Graceful Degradation** (`fallback.py`): Multi-strategy fallback chains

### Security Features (`src/util/`)
- **Secure Logging** (`secure_logging.py`): API key sanitization and structured logging
- **Input Validation** (`../models/models.py`): Pydantic models with strict validation
- **Exception Handling** (`exceptions.py`): Custom exception hierarchy 

**Key Design Principle:** All domain knowledge lives in `strategic-searches.yaml` and your documents. The Python code is generic and requires no modification for different document domains.

## 🔒 Security

This project implements comprehensive security measures to protect API keys and sensitive data.

### Secret Scanning

**Automated secret detection** prevents accidental commits of API keys:

```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Hooks automatically run on git commit
# Scan manually anytime:
uv run detect-secrets scan
```

**CI/CD Integration**: GitHub Actions automatically scans all pushes and PRs for secrets.

📖 **See [SECURITY_SCANNING.md](./SECURITY_SCANNING.md)** for complete setup and troubleshooting.

### Security Features

✅ **API Key Protection:**
- **Windows DPAPI encryption** via Python ctypes (no PowerShell execution policy requirements)
- **Unified credential target**: `pinecone_API_KEY` in Windows Credential Manager (shared across all Pinecone MCPs)
- **Unified key file**: `~/.pinecone_api_key` — bytes 0–31 = DPAPI entropy prefix, bytes 32+ = encrypted key (self-contained; no separate entropy file)
- **Shared entropy source**: `~/.uspto_internal_auth_secret` — created automatically on first use; reused by all USPTO and Pinecone MCPs ("first wins" pattern)
- **Cross-platform fallback** to environment variables on Linux/macOS — `PINECONE_API_KEY` (canonical) then `PINECONE_ASSISTANT_API_KEY` (legacy)
- **No plain text storage** in Claude Desktop configuration files
- Environment variable validation with format checking
- API keys never logged (automatic sanitization via `src/secure_logging.py`)
- Pre-commit hooks prevent accidental commits
- CI/CD scanning in GitHub Actions
- 20+ secret types detected (AWS keys, GitHub tokens, JWT, private keys, API keys, and more)

✅ **Secure Communication:**
- HTTPS enforced for production environments
- HTTP allowed only for localhost in development
- Configurable timeout protection (default: 30s)
- Request ID tracking for security monitoring

✅ **Error Handling:**
- Sensitive information automatically redacted from logs
- Custom exception hierarchy for precise error handling (`src/exceptions.py`)
- Debug mode controls traceback exposure
- User-friendly error messages without internal details
- Security event logging for validation failures

✅ **Input Validation:**
- API key format validation (prefix, length, characters)
- Assistant name validation
- Model parameter whitelisting
- Request size limits
- Pydantic models with strict validation (`src/models.py`)

✅ **Resilience Features:**
- Circuit breaker pattern prevents cascading failures
- Exponential backoff retry with jitter
- Resource isolation via bulkhead pattern
- In-memory response caching with TTL
- Graceful degradation strategies

📖 **See [SECURITY_GUIDELINES.md](./SECURITY_GUIDELINES.md)** for best practices and incident response procedures.

## 🧪 Development & Testing

### Test Suite

**Comprehensive test coverage** with 144 tests across 8 test files:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing
```

**Test Statistics:**
- ✅ **144/144 tests passing (100%)**
- ✅ **100% type hint coverage**
- ✅ **Comprehensive package documentation**
- ✅ **Shared test fixtures** for maintainability

### Test Categories

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_basic.py` | 19 | Configuration, models, strategic search patterns |
| `test_integration.py` | 17 | End-to-end workflows, all 6 MCP tools |
| `test_resilience.py` | 25 | Retry, circuit breaker, cache, bulkhead, fallback |
| `test_security.py` | 25 | API key handling, secure logging, validation |
| `test_unified_credential.py` | 15 | Unified credential architecture (`pinecone_API_KEY`, `~/.pinecone_api_key`, env var fallback chain) |
| `test_entropy_security.py` | 15 | DPAPI encryption, embedded entropy format, tamper detection |
| `test_security_audit.py` | 14 | Static codebase scans, hardcoded entropy detection, file permissions |
| `test_monitoring.py` | 14 | Health checks, metrics, circuit breaker state reporting |

### Code Quality

**Type Safety:**
- All functions have complete type hints
- Pydantic models for request/response validation
- Ready for static analysis with mypy

**Documentation:**
- Comprehensive docstrings for all packages
- Usage examples in module documentation
- API documentation auto-generated from types

**Test Infrastructure:**
- Shared fixtures in `tests/conftest.py`
- Automatic secure storage mocking
- Consistent mock data across test suite

📖 **See [tests/README.md](./tests/README.md)** for detailed test documentation and development guidelines.

##  📄License

MIT **[License](LICENSE)**

## ⚠️ Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND.**

**Independent Project Notice**: This is an independent personal project and is not affiliated with, endorsed by, or sponsored by the United States Patent and Trademark Office (USPTO) and/or Pinecone Systems, Inc.

The author makes no representations or warranties, express or implied, including but not limited to:

- **Accuracy & AI-Generated Content**: No guarantee of data accuracy, completeness, or fitness for any purpose. Users are specifically cautioned that outputs generated or assisted by Artificial Intelligence (AI) components, including but not limited to text, data, or analyses, may be inaccurate, incomplete, fictionalized, or represent "hallucinations" (confabulations) by the AI model.
- **Availability**: Pinecone dependencies may cause service interruptions.
- **Legal Compliance**: Users are solely responsible for ensuring their use of this software, and any submissions or actions taken based on its outputs, strictly comply with all applicable laws, regulations, and policies, including but not limited to:
  - The latest [Guidance on Use of Artificial Intelligence-Based Tools in Practice Before the United States Patent and Trademark Office](https://www.federalregister.gov/documents/2024/04/11/2024-07629/guidance-on-use-of-artificial-intelligence-based-tools-in-practice-before-the-united-states-patent) (USPTO Guidance).
  - The USPTO's Duty of Candor and Good Faith (e.g., 37 CFR 1.56, 11.303), which includes a duty to disclose material information and correct errors.
  - The USPTO's signature requirements (e.g., 37 CFR 1.4(d), 2.193(c), 11.18), certifying human review and reasonable inquiry.
  - All rules regarding inventorship (e.g., each claimed invention must have at least one human inventor).
- **Legal Advice**: This tool provides data access and processing only, not legal counsel. All results must be independently verified, critically analyzed, and professionally judged by qualified legal professionals.
- **Commercial Use**: Users must verify Pinecone terms for commercial applications.
- **Confidentiality & Data Security**: The author makes no representations regarding the confidentiality or security of any data, including client-sensitive or technical information, input by the user into the software's AI components or transmitted to third-party AI services (e.g., Pinecone, and Pinecone's use of OpenAI, Anthropic and Google). Users are responsible for understanding and accepting the privacy policies, data retention practices, and security measures of any integrated third-party AI services.
- **Foreign Filing Licenses & Export Controls**: Users are solely responsible for ensuring that the input or processing of any data, particularly technical information, through this software's AI components does not violate U.S. foreign filing license requirements (e.g., 35 U.S.C. 184, 37 CFR Part 5) or export control regulations (e.g., EAR, ITAR). This includes awareness of potential "deemed exports" if foreign persons access such data or if AI servers are located outside the United States.

**LIMITATION OF LIABILITY:** Under no circumstances shall the author be liable for any direct, indirect, incidental, special, or consequential damages arising from use of this software, even if advised of the possibility of such damages.

### USER RESPONSIBILITY: YOU ARE SOLELY RESPONSIBLE FOR THE INTEGRITY AND COMPLIANCE OF ALL FILINGS AND ACTIONS TAKEN BEFORE THE USPTO.

- **Independent Verification**: All outputs, analyses, and content generated or assisted by AI within this software MUST be thoroughly reviewed, independently verified, and corrected by a human prior to any reliance, action, or submission to the USPTO or any other entity. This includes factual assertions, legal contentions, citations, evidentiary support, and technical disclosures.
- **Duty of Candor & Good Faith**: You must adhere to your duty of candor and good faith with the USPTO, including the disclosure of any material information (e.g., regarding inventorship or errors) and promptly correcting any inaccuracies in the record.
- **Signature & Certification**: You must personally sign or insert your signature on any correspondence submitted to the USPTO, certifying your personal review and reasonable inquiry into its contents, as required by 37 CFR 11.18(b). AI tools cannot sign documents, nor can they perform the required human inquiry.
- **Confidential Information**: DO NOT input confidential, proprietary, or client-sensitive information into the AI components of this software without full client consent and a clear understanding of the data handling practices of the underlying AI providers. You are responsible for preventing inadvertent or unauthorized disclosure.
- **Export Controls**: Be aware of and comply with all foreign filing license and export control regulations when using this tool with sensitive technical data.
- **Service Compliance**: Ensure compliance with all USPTO (e.g., Terms of Use for USPTO websites, USPTO.gov account policies, restrictions on automated data mining) and Pinecone terms of service. AI tools cannot obtain USPTO.gov accounts.
- **Security**: Maintain secure handling of API credentials and client information.
- **Testing**: Test thoroughly before production use.
- **Professional Judgment**: This tool is a supplement, not a substitute, for your own professional judgment and expertise.

**By using this software, you acknowledge that you have read this disclaimer and agree to use the software at your own risk, accepting full responsibility for all outcomes and compliance with relevant legal and ethical obligations.**

> **Note for Legal Professionals:** While this tool provides strategic patent research patterns commonly used in legal practice, it is a data retrieval and AI-assisted processing system only. All results require independent verification, critical professional analysis, and cannot substitute for qualified legal counsel, official USPTO resources, or the exercise of your personal professional judgment and duties outlined in the USPTO Guidance on AI Use.

##  🔗Related Links

- **[Pinecone](https://www.pinecone.io/)**
- [**USPTO**](https://www.uspto.gov/)
- [Manual of Patent Examining Procedure (MPEP)](https://www.uspto.gov/web/offices/pac/mpep/index.html)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude](https://claude.ai)
- [uv Package Manager](https://github.com/astral-sh/uv)

## 💝 Support This Project

If you find this Pinecone Assistant MCP Server useful, please consider supporting the development! This project was developed during my personal time over many hours to provide a comprehensive, production-ready tool for the patent community.

[![Donate with PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/walkoe)

Your support helps maintain and improve this open-source tool for everyone in the patent community. Thank you!

##  Acknowledgments

- **[Pinecone](https://www.pinecone.io/)** for providing Pinecone Assistants
- [Model Context Protocol](https://modelcontextprotocol.io/) for the MCP specification
- **[Claude Code](https://claude.ai/code)** for exceptional development assistance, architectural guidance, documentation creation, PowerShell automation, test organization, and comprehensive code development throughout this project
- **[Claude Desktop](https://claude.ai)** for additional development support and testing assistance

---

**Questions?** See [INSTALL.md](INSTALL.md) for complete cross-platform installation guide or review the test scripts for working examples.