# Pinecone MCP Server Comparison

A comprehensive comparison of five different Pinecone MCP (Model Context Protocol) server implementations for integrating Pinecone with Claude Desktop, Claude Code, Cursor, and other MCP clients.  The 2 Official Pinecone MCP Servers and the author's planned 3 Pinecone MCP servers.

## Quick Reference Table

| Feature | Official Assistant MCP | Official Vector DB MCP | pinecone_assistant_mcp (this repo) | pinecone_rag_mcp *(future release)* | pinecone_diff_rag_mcp *(future release)* |
|---------|----------------------|------------------------|-----------------------------------|------------------|------------------------------------------|
| **GitHub** | [pinecone-io/assistant-mcp](https://github.com/pinecone-io/assistant-mcp) | [pinecone-io/pinecone-mcp](https://github.com/pinecone-io/pinecone-mcp) | [john-walkoe/pinecone_assistant_mcp](https://github.com/john-walkoe/pinecone_assistant_mcp) | [john-walkoe/pinecone_rag_mcp](https://github.com/john-walkoe/pinecone_rag_mcp) | [john-walkoe/pinecone_diff_rag_mcp](https://github.com/john-walkoe/pinecone_diff_rag_mcp) |
| **Language** | TypeScript/Docker | TypeScript/NPM | Python | TypeScript/NPM | Python |
| **Status** | Early Access | Early Access | Production-Ready | *Future Release* | *Future Release* |
| **Installation** | Docker or Remote HTTP | NPM Package | Python/uv | NPM | Python/uv |
| **Document Upload Scripts** | ❌ None | ❌ None | ✅ Automated via Install and Upload Scripts | ✅ Automated via Install and Upload Scripts + Web UI | ✅ Automated via Install and Upload Scripts + Web UI |
| **Primary Use Case** | Simple context retrieval | Index management & inference | Full Assistant API capabilities | Direct vector search with custom embeddings | Version-aware document analysis (contracts, policies) |
| **API Used** | Pinecone Assistant API | Pinecone Vector DB API + Inference | Pinecone Assistant API | Pinecone Vector DB API | Pinecone Vector DB API (3 indexes) |

## Detailed Comparison

### 1. Official Pinecone Assistant MCP
**GitHub:** https://github.com/pinecone-io/assistant-mcp

#### Overview
Official Pinecone implementation providing direct access to Assistant's context retrieval functionality. Minimal feature set focused on document snippet retrieval.

> **Verified:** The server (Rust implementation) exposes a single tool that calls the `/assistant/chat/{name}/context` endpoint — the **context-only** API. The full Pinecone chat endpoint (which invokes Pinecone's AI model to synthesize an answer) is **never called**. This is a pure snippet retrieval layer with no AI synthesis capability.

#### Key Features
- ✅ **Single Tool:** `assistant_context` - Get relevant document snippets (raw, no AI synthesis)
- ✅ **Remote MCP Support:** Can connect via HTTPS endpoint (no local setup required)
- ✅ **Local Docker Option:** Run containerized MCP server
- ✅ **Streamable HTTP Transport:** Compatible with MCP clients supporting HTTP streaming
- ❌ **No Chat API Access:** Calls the `/context` endpoint only — Pinecone's AI model is never invoked
- ❌ **No Delegation / Agentic Synthesis:** Cannot delegate research to Pinecone AI; unsuitable for workflows where Claude offloads synthesis to preserve its own context window
- ❌ **No Strategic Search:** Single query at a time only
- ❌ **No Configuration Switching:** Cannot switch assistants mid-conversation

#### Pros
- ✅ **Official Pinecone Support:** Maintained by Pinecone team
- ✅ **Remote Option:** No local infrastructure needed
- ✅ **Simple Setup:** Minimal configuration required
- ✅ **Streamable HTTP:** Works with modern MCP clients

#### Cons
- ❌ **Context Retrieval Only:** Calls `/context` endpoint — raw snippets returned, Pinecone AI never runs
- ❌ **No Delegation or Agentic Support:** Cannot have Pinecone AI synthesize answers to preserve Claude's context window; not suitable for agentic workflows where an orchestrating LLM delegates sub-tasks
- ❌ **No Advanced Features:** No strategic search, multi-search, or assistant switching
- ❌ **Early Access:** Not production-ready per Pinecone docs
- ❌ **Proxy Required:** Claude Desktop needs supergateway workaround for remote

#### Best For
- Users who **already have populated assistants** and only need raw document snippet retrieval
- Claude Code users who want minimal setup (native HTTP support, no local install)
- Workflows where **Claude itself** performs all synthesis (raw chunks flow into Claude's context)

#### ❌ Not suitable for
- Agentic workflows where synthesis should be delegated to Pinecone AI
- Preserving Claude's context window by offloading research to a sub-agent
- Any use case requiring the Pinecone Assistant chat/AI capabilities

#### ⚠️ Important Limitations
- **No document upload tools in MCP** - You must manually create and populate your assistant via Pinecone web UI or API before using this MCP
- **No AI synthesis** - The Pinecone Assistant's AI model is never called; all document understanding must happen in Claude's own context

---

### 2. Official Pinecone Vector Database MCP
**NPM Package:** @pinecone-database/mcp

**GitHub:** https://github.com/pinecone-io/pinecone-mcp

#### Overview
Official Pinecone MCP for direct vector database operations with integrated inference support. Focused on index management and embeddings, not Assistant API.

#### Key Features
- ✅ **Documentation Search:** `search-docs` - Search Pinecone documentation
- ✅ **Index Management:** `list-indexes`, `describe-index`, `describe-index-stats`
- ✅ **Index Creation:** `create-index-for-model` - Create indexes with integrated inference
- ✅ **Data Operations:** `upsert-records` - Add/update vectors with integrated embeddings
- ✅ **Search Operations:** `search-records` - Query with text (auto-embedded)
- ✅ **Advanced Search:** `cascading-search` - Multi-index search with deduplication
- ✅ **Reranking:** `rerank-documents` - Rerank search results
- ❌ **Integrated Inference Only:** Doesn't support custom embeddings (Ollama/OpenAI/Cohere)
- ❌ **No Strategic Patterns:** No domain-specific multi-search patterns
- ❌ **Read/Write:** Includes upsert operations (not read-only)

#### Pros
- ✅ **Official Pinecone Support:** Maintained by Pinecone team
- ✅ **Full Index Management:** Create, configure, and monitor indexes
- ✅ **Integrated Inference:** Auto-embeddings with Pinecone models
- ✅ **Multi-Index Support:** Cascading search across indexes
- ✅ **Documentation Access:** Built-in Pinecone docs search
- ✅ **Easy Install:** NPM package, no build required

#### Cons
- ❌ **Early Access:** Not production-ready per Pinecone docs
- ❌ **Integrated Inference Only:** Can't use with existing Ollama/OpenAI/Cohere embeddings
- ❌ **No Domain Patterns:** Generic search, no strategic multi-search
- ❌ **Write Operations:** Includes upsert (may not want in production)
- ❌ **No Assistant API:** Different from Assistant features (chat, etc.)

#### Best For
- Users creating new indexes with Pinecone integrated inference
- Development and testing workflows
- Index management and monitoring
- Pinecone documentation reference during development
- Users who want official support

#### ⚠️ Important Limitation
- **No bulk upload scripts** - Has `upsert-records` tool for individual records, but no automated scripts for processing and uploading document collections. You must write your own upload logic or manually add records.

---

### 3. pinecone_assistant_mcp (This Repository)
**GitHub:** https://github.com/john-walkoe/pinecone_assistant_mcp

#### Overview
Python-based MCP providing full Pinecone Assistant API capabilities with strategic search patterns, AI chat, and assistant switching. Production-ready with comprehensive security and resilience features.

#### Key Features
- ✅ **Full Assistant API Access:** All Pinecone Assistant capabilities
- ✅ **AI-Powered Chat:** `assistant_chat` - Multi-turn conversations with citations (response is clean text: answer + Sources section + token summary line)
- ✅ **Strategic Multi-Search:** `assistant_strategic_multi_search_chat` - Domain-specific research patterns
- ✅ **Context Retrieval:** `assistant_context` - Raw document retrieval with multimodal support and multi-turn messages input (free tier friendly)
- ✅ **Strategic Context:** `assistant_strategic_multi_search_context` - Multi-search without AI (saves tokens)
- ✅ **Assistant Switching:** `update_configuration` - Switch between up to 5 assistants mid-conversation
- ✅ **Configuration Status:** `get_configuration_status` - Check current settings
- ✅ **Answer Evaluation:** `evaluate_answer` - Score AI answers against ground truth (paid plan)
- ✅ **MCP Prompts:** 4 corpus-neutral prompt templates (`deep_research`, `quick_lookup`, `comparative_research`, `delegated_research`) accessible from the Claude prompt menu
- ✅ **Claude Skills:** 3 included skills for guided workflows (generic, USPTO-specific, paid-plan delegation)
- ✅ **YAML-Configurable:** Customize search patterns without code changes
- ✅ **Windows DPAPI Security:** Encrypted API key storage on Windows
- ✅ **Production Resilience:** Circuit breaker, retry logic, caching, bulkhead pattern
- ✅ **Multi-Assistant Support:** Work with up to 5 assistants (free tier) in one session
- ✅ **Automated Setup:** Windows and Linux setup scripts with document upload
- ✅ **Document Upload:** Includes USPTO MPEP documents as reference implementation
- ✅ **Model Selection:** Choose GPT-4o, Claude, or Gemini models

#### Token Usage Optimization
- **Context-only tools** (assistant_context, assistant_strategic_multi_search_context):
  - Uses context tokens (Free tier 500k lifetime usage)
  - No AI costs
  - Recommended for 90% of queries
- **AI-powered tools** (assistant_chat, assistant_strategic_multi_search_chat):
  - Uses Chat input + Chat output tokens (Free tier 1.5M/200k lifetime usage)
  - Reserve for complex synthesis questions, main chat token conservation and agentic workflows

#### Free Tier Limitations
**CRITICAL:** Token limits are **LIFETIME per project, NOT monthly**:
- Context tokens: 500K total
- Input tokens: 1.5M total
- Output tokens: 200K total

**Paid Plan Costs:**
- Standard: $50/month minimum + $0.05/hour per assistant + token costs
- See [pricing documentation](README.md#token-usage-optimization) for details

#### Pros
- ✅ **Full Feature Set:** All Assistant API capabilities
- ✅ **Strategic Search:** Pre-configured multi-search patterns for patent law (customizable for any domain)
- ✅ **Multi-Assistant:** Switch between 5 assistants mid-conversation
- ✅ **Production Ready:** Comprehensive resilience and security features
- ✅ **Free Tier Optimized:** Context-only tools maximize free usage
- ✅ **Automated Setup:** Complete deployment scripts with document upload
- ✅ **USPTO Documents:** Reference implementation with patent examination materials
- ✅ **Secure Storage:** Windows DPAPI encryption for API keys
- ✅ **Comprehensive Docs:** Detailed installation, usage, and customization guides

#### Cons
- ❌ **Python Dependency:** Requires Python 3.11+ and uv package manager
- ❌ **Assistant API Only:** Doesn't support direct vector operations
- ❌ **Pinecone Costs:** Uses Pinecone Assistant API (see pricing above)
- ❌ **File Upload Required:** Documents must be uploaded to Assistant

#### Best For
- **Production use** with Pinecone Assistant API
- **Strategic research** requiring multi-pattern searches
- **Multi-assistant workflows** (legal research, medical literature, technical docs)
- **Patent law** or other domain-specific research (customizable)
- **Windows users** needing secure API key storage
- Users who want **AI-powered synthesis** with citations

---

### 4. pinecone_rag_mcp *(future release)*
**GitHub:** https://github.com/john-walkoe/pinecone_rag_mcp

#### Overview
TypeScript-based MCP providing direct Pinecone vector database access with quad embedding provider support (Ollama/OpenAI/Cohere/Pinecone). Retrieval-only design for production safety, with context expansion capabilities via `fetch_chunks`.

#### Key Features
- ✅ **Quad Embedding Support:** Ollama (local), OpenAI (cloud), Cohere (enterprise), Pinecone (native)
- ✅ **Semantic Search:** `semantic_search` - Natural language queries
- ✅ **Strategic Multi-Search:** `strategic_multi_search` - Domain-specific research patterns
- ✅ **Context Expansion:** `fetch_chunks` - Direct chunk retrieval by ID, metadata filter, or prefix for neighbor/section/document expansion patterns (see below)
- ✅ **Web Document Manager:** `start_document_manager` - Browser UI for browsing, viewing, deleting, and uploading documents; launches at `http://localhost:8888` (configurable)
- ✅ **YAML-Configurable:** Customize search patterns without code changes
- ✅ **Runtime Configuration:** `update_configuration` - Change settings without restart
- ✅ **Index Monitoring:** `get_index_stats` - Monitor vector counts and namespaces
- ✅ **Namespace Support:** `DEFAULT_NAMESPACE` for workspace isolation
- ✅ **Retrieval-Only (MCP tools):** MCP search/fetch tools are read-only; document management (upload/delete) is handled via the separate web UI
- ✅ **Dimension Validation:** Auto-checks embedding/index compatibility
- ✅ **Custom Embeddings:** Full control over embedding models
- ✅ **Document Upload Scripts:** TypeScript tools for uploading with custom embeddings
- ✅ **Free Tier Friendly:** Works with free Pinecone tier
- ✅ **USPTO Documents:** Reference implementation with patent examination materials

#### Context Expansion with `fetch_chunks`

RAG agents fail when they receive isolated fragments that lack structural context — a chunk may say "the policy was updated" but the agent has no idea *what* policy or *what changed* because the surrounding document structure is lost during chunking.  (Based on [The AI Automators' research](https://www.youtube.com/watch?v=y72TrpffdSk))

`fetch_chunks` solves this by providing direct access to Pinecone's fetch and list APIs **without requiring a new embedding** — enabling context expansion patterns after `semantic_search` returns candidate chunks:

| Expansion Pattern | How `fetch_chunks` Enables It |
|-------------------|-------------------------------|
| **Neighbor expansion** | Fetch adjacent chunk IDs (chunk N-1, N+1) around the retrieved chunk |
| **Section expansion** | Fetch a range of IDs covering a document section (e.g., chunks 19–25) |
| **Document expansion** | Fetch all chunks from one document using `metadataFilter: {"doc_id": "..."}` |
| **Prefix discovery** | List all chunk IDs under a document prefix, then fetch the relevant range |

**Three modes** (which parameter you provide determines the Pinecone API used):

| Mode | Parameter | Pinecone API Called | Returns |
|------|-----------|---------------------|---------|
| **Fetch by IDs** | `ids: ["chunk_0", "chunk_1"]` | `index.fetch()` | Full text + metadata for each ID |
| **Fetch by metadata** | `metadataFilter: {"doc_id": "x"}` | `POST /vectors/fetch_by_metadata` | All matching chunks (paginated) |
| **List by prefix** | `prefix: "MPEP 2106"` | `index.listPaginated()` | IDs only — follow up with IDs mode |

**Key parameters:**
- `fields` — Return only selected metadata fields (token optimization)
- `limit` — Up to 1000 results for metadata mode, 100 for prefix/IDs
- `paginationToken` — Continue multi-page fetches
- `namespace` — Falls back to `DEFAULT_NAMESPACE`

**Typical workflow:**
```
1. semantic_search("Section 101 practical application") → returns candidate chunks with IDs
2. fetch_chunks(ids=["mpep_2106_chunk_12", "mpep_2106_chunk_13", "mpep_2106_chunk_14"])
   → expands context to neighboring chunks for full section coverage
```

#### Web Document Manager (`start_document_manager`)

Launches a localhost Express server with a browser-based document management UI. Invoke the tool once per session; the server stays running until Claude restarts.

**Capabilities:**

| Feature | Details |
|---------|---------|
| Browse documents | List all documents grouped by doc ID, with chunk counts and metadata |
| View chunks | Sample first/middle/last chunks, view full metadata per record |
| Delete documents | Permanently removes all chunks for a document from Pinecone |
| Upload documents | Upload new files and index them (with chunking + embedding) |
| Namespace switching | Select and filter by namespace via UI dropdown |
| Index statistics | Live vector count, dimensions, index fullness |

**Upload file type limitation:** Only `.md` and `.txt` files are accepted. PDF, DOCX, JSON and other formats must be converted before uploading via the UI. (The standalone `deploy/upload_files` scripts support a broader set of formats.)

**Access:** `http://localhost:8888` (port configurable via `port` parameter or `DOCUMENT_MANAGER_PORT` env var). Localhost-only — not exposed externally.

#### Embedding Providers
- **Ollama:** nomic-embed-text (768 dims) - Local, free, private
- **OpenAI:** text-embedding-3-small/large (1536/3072 dims) - Cloud, pay-per-use
- **Cohere:** embed-english/multilingual-v3.0 (1024 dims) - Enterprise, 100+ languages
- **Pinecone:** llama-text-embed-v2 (1024+ dims) - Native, 12x faster than OpenAI, $0.16/1M tokens

#### Pros
- ✅ **Flexible Embeddings:** Choose Ollama/OpenAI/Cohere/Pinecone based on needs
- ✅ **Local Option:** Ollama for completely offline/private embeddings
  - ✅ **Support for prefixing** that can improve RAG results by up to 2x (Based on [Matt Williams' research](https://www.youtube.com/watch?v=76EIC_RaDNw&list=PLvsHpqLkpw0fIT-WbjY-xBRxTftjwiTLB))

- ✅ **Strategic Search:** Customizable multi-pattern research
- ✅ **Context Expansion:** `fetch_chunks` for neighbor/section/document expansion without re-embedding
- ✅ **Web Document Manager:** Browser UI for document browsing, deletion, and upload (.md/.txt)
- ✅ **Production Safe:** MCP search tools are read-only; destructive operations only via explicit web UI
- ✅ **Free Tier Compatible:** Pinecone free tier (1 serverless index) + free embeddings (Ollama or Pinecone 5M tokens/month)
- ✅ **Namespace Support:** Easy workspace/tenant isolation
- ✅ **TypeScript:** Modern, type-safe implementation
- ✅ **Fast Setup:** NPM package with automated scripts

#### Cons
- ❌ **Future Release:** Not yet publicly available
- ❌ **No AI Chat:** Retrieval only (no LLM synthesis like Assistant API)
- ❌ **Manual Upload:** Must upload documents yourself with embeddings
- ❌ **No Citations:** Returns raw text (no text highlights or structured citations)
- ❌ **Embedding Consistency:** Must use same embeddings for indexing and querying
- ❌ **Index Management:** Need to create and configure indexes separately

#### Best For
- Users with **existing Pinecone vector databases**
- **Local embeddings** with Ollama (privacy/offline)
  - Support for prefixing that can improve RAG results by up to 2x (Based on [Matt Williams' research](https://www.youtube.com/watch?v=76EIC_RaDNw&list=PLvsHpqLkpw0fIT-WbjY-xBRxTftjwiTLB))

- **Custom embedding workflows** (OpenAI/Cohere/Pinecone flexibility)
- **Agentic RAG workflows** needing context expansion — retrieve candidate chunks via `semantic_search`, then expand to neighbors/sections/full documents via `fetch_chunks`
- **Multi-tenant applications** (namespace isolation)
- **Production safety** (read-only operations)
- **Free tier maximization** (Ollama embeddings = $0 cost)
- Users who want **full control** over embeddings and indexing

---

### 5. pinecone_diff_rag_mcp *(Future Release)*
**GitHub:** https://github.com/john-walkoe/pinecone_diff_rag_mcp

#### Overview
Python-based MCP for **version-aware document analysis** with deduplicated storage and change-only retrieval. Designed for multi-version documents — contracts, policies, legal agreements, technical specs — where tracking *what changed* between versions is as important as *what the document says*. Uses three separate Pinecone indexes (content, version, diff) plus a SQLite metadata cache. Includes a full MCP App web UI that auto-starts with the server. (Based on [VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents](https://arxiv.org/pdf/2510.08109))

**Key Innovation:** Instead of storing 10 versions of a contract (10× storage), the server stores each unique clause **once** and tracks versions via pointers (~90% storage reduction). When querying "what changed?", only the diff index is searched — no duplicate content returned.

#### Key Features
- ✅ **Deduplicated Storage:** Each unique clause stored once (hash-based deduplication, ~90% storage reduction)
- ✅ **Change-Only Retrieval:** Diff index stores only changed clauses; search changes without duplicate content noise
- ✅ **Version Reconstruction:** Rebuild any historical version on-demand from base + deltas
- ✅ **Negotiation Analysis:** `analyze_negotiation_patterns` identifies concessions, firm positions, and negotiation dynamics
- ✅ **Intent-Aware Routing:** `classify_and_search` auto-classifies queries (CONTENT / CHANGE / VERSION / COMPARISON / NEGOTIATION) and routes to the appropriate tool
- ✅ **MCP App Web UI:** FastAPI-based document manager auto-starts with server — drag-and-drop upload, version timeline, visual side-by-side diff viewer, negotiation analysis view
- ✅ **Multi-Format Extraction:** PDF (PyPDF2 → Docling → Mistral OCR chain), DOCX, DOC, TXT, Markdown
- ✅ **OpenAI-Compatible Embeddings:** Works with OpenAI, Ollama (local/free), OpenRouter, or any compatible endpoint
- ✅ **Cohere Reranking:** Optional reranking for improved result relevance
- ✅ **Smart Version Detection:** Auto-detects `contract_v1.pdf` → `doc_id="contract"`, `version="1.0"` from filenames
- ✅ **Fuzzy doc_id Resolution:** Partial names (e.g. `"Smith Contract"`) resolved against known doc IDs at query time
- ❌ **No AI-Powered Chat:** Retrieval only — no LLM synthesis like the Assistant API
- ❌ **Version-Aware Use Cases Only:** Overkill for single-version document search (use pinecone_rag_mcp instead)

#### MCP Tools (11 total)

| Tool | Purpose |
|------|---------|
| `start_document_manager` | Return URL of the running web UI (auto-starts with server) |
| `test_configuration` | Validate config and connectivity |
| `get_index_stats` | Get Pinecone index statistics |
| `search_content` | Search deduplicated content (no duplicates across versions) |
| `search_changes` | Search only changed clauses across versions |
| `get_version_timeline` | Get version history with change counts |
| `compare_versions` | Compare two specific versions side-by-side |
| `trace_clause_evolution` | See how a clause evolved across all versions |
| `reconstruct_version` | Rebuild a historical version on-demand |
| `analyze_negotiation_patterns` | Identify concessions and firm positions across versions |
| `classify_and_search` | Auto-route query to appropriate tool based on intent |

#### Three-Index Architecture

| Index | Contents | Use |
|-------|----------|-----|
| **Content Index** | Deduplicated unique clause text (hash-based) | "What does clause X say?" |
| **Version Index** | Metadata pointers (`version → clause_id → content_hash`, dummy vectors) | "What clauses are in v1.0?" |
| **Diff Index** | Changed clauses only (`old_text + new_text + change_summary`) | "How did clause X change?" |

#### Example Queries

```
# Content query → search_content
"What does the current indemnity clause say?"

# Change query → search_changes
"How did the liability cap change between v1 and v2?"

# Version query → get_version_timeline
"What versions exist for the MSA with VendorX?"

# Comparison → compare_versions
"Compare v1.0 and v2.0 of the service agreement"

# Negotiation analysis → analyze_negotiation_patterns
"Analyze the last 10 versions. Are they making concessions?"
```

#### Pros
- ✅ **Purpose-Built for Versioned Docs:** Only MCP server designed for multi-version document workflows
- ✅ **~90% Storage Reduction:** Deduplication eliminates redundant clause storage
- ✅ **Precise Change Retrieval:** Search only what actually changed — no false positives from unchanged duplicates
- ✅ **Rich Analysis Tools:** Negotiation patterns, clause evolution, version reconstruction
- ✅ **Local Embeddings:** Ollama support for $0 embedding cost
  - ✅ **Support for prefixing** that can improve RAG results by up to 2x (Based on [Matt Williams' research](https://www.youtube.com/watch?v=76EIC_RaDNw&list=PLvsHpqLkpw0fIT-WbjY-xBRxTftjwiTLB))

- ✅ **Integrated Web UI:** MCP App auto-starts — no separate setup
- ✅ **Multi-Format Extraction:** Full PDF/DOCX extraction chain including OCR fallback
- ✅ **Intent-Aware Routing:** `classify_and_search` handles ambiguous queries automatically

#### Cons
- ❌ **Future Release:** Not yet publicly available
- ❌ **3 Pinecone Indexes Required:** Uses 3× the index slots vs. single-index MCPs (Starter plan: 5 indexes total)
- ❌ **Version-Specific Use Case:** Not optimal for single-version document corpora
- ❌ **No AI Synthesis:** Returns raw text; no AI-generated summaries or citations
- ❌ **LLM Required for Routing:** `classify_and_search` requires an OpenAI-compatible chat model
- ❌ **Complex Setup:** 3 indexes to create, SQLite to initialize vs. single index for other MCPs

#### Best For
- **Contract lifecycle management** — tracking every revision through negotiation
- **Policy version control** — "what changed in the Q3 compliance update?"
- **Legal document evolution** — how terms shifted across agreement versions
- **Negotiation intelligence** — identifying which party is making concessions and which is holding firm
- **Technical spec versioning** — API changes, requirement updates, architecture decisions
- **Any workflow where diff matters more than content**

#### ❌ Not Suitable For
- Single-version document search (use **pinecone_rag_mcp** instead)
- AI-powered synthesis with citations (use **pinecone_assistant_mcp** instead)
- Users who need only simple semantic search without version awareness

---

## Use Case Decision Matrix

### Choose Official Assistant MCP if:
- ✅ You only need raw document snippets returned to Claude (Claude does all synthesis)
- ✅ You want minimal setup (remote option, no local install)
- ✅ You're using Claude Code (native HTTP support)
- ✅ You're testing Pinecone Assistant integration quickly
- ❌ Avoid if: You need AI synthesis, delegation to Pinecone's AI, agentic workflows, context window preservation, strategic search, or production features
- ❌ Avoid if: You want Pinecone to act as a sub-agent and return synthesized results — the chat API is not exposed

### Choose Official Vector DB MCP if:
- ✅ You're creating new indexes with Pinecone integrated inference
- ✅ You need index management tools
- ✅ You want official Pinecone support
- ✅ You need documentation search during development
- ❌ Avoid if: You have existing custom embeddings (Ollama/OpenAI/Cohere)

### Choose pinecone_assistant_mcp if:
- ✅ You need **AI-powered chat** with citations (the only option exposing the Pinecone chat API)
- ✅ You want to **delegate synthesis to Pinecone AI** — receive compact answers instead of raw chunks, preserving Claude's context window
- ✅ You're building **agentic workflows** where Claude orchestrates research tasks delegated to Pinecone
- ✅ You want **strategic multi-search** for domain research
- ✅ You need to **switch between multiple assistants** mid-conversation
- ✅ You need **production resilience** (retry, circuit breaker, caching)
- ✅ You're doing **patent law** or other specialized domain research
- ✅ You prefer **Python** ecosystem
- ❌ Avoid if: Free tier costs concern you (tokens are lifetime limits)

### Choose pinecone_rag_mcp if *(Future Release)*:
- ✅ You have **existing vector databases** with custom embeddings
- ✅ You want **local embeddings** with Ollama (privacy/offline)
- ✅ You need **embedding flexibility** (OpenAI/Cohere/Pinecone options)
- ✅ You need **context expansion** — retrieve candidate chunks then expand to neighbors, sections, or full documents without re-embedding (`fetch_chunks`)
- ✅ You want a **browser UI** to browse, inspect, and manage indexed documents (`start_document_manager`)
- ✅ You want **read-only MCP tools** with document management gated behind an explicit web UI
- ✅ You need **namespace isolation** for multi-tenancy
- ✅ You want **free tier optimization**
- ✅ You prefer **TypeScript** ecosystem
- ❌ Avoid if: You need AI synthesis or structured citations

### Choose pinecone_diff_rag_mcp if *(Future Release)*:
- ✅ Your documents **have multiple versions** and you need to track what changed
- ✅ You're working with **contracts** and need to identify concessions, firm positions, and negotiation patterns
- ✅ You need to **compare two specific versions** side-by-side with clause-level granularity
- ✅ You want to **search only changed content** — not duplicate unchanged clauses across versions
- ✅ You need to **reconstruct historical versions** on-demand
- ✅ You want **~90% storage reduction** vs. storing full copies of each document version
- ✅ You want an **integrated MCP App web UI** with drag-and-drop upload and visual diff viewer
- ✅ You want **local/free embeddings** with Ollama
- ❌ Avoid if: Your documents are single-version (use pinecone_rag_mcp for simpler semantic search)
- ❌ Avoid if: You need AI-powered synthesis with citations (use pinecone_assistant_mcp)

---

## Feature Comparison Matrix

| Feature | Official Assistant | Official Vector DB | pinecone_assistant_mcp | pinecone_rag_mcp *(future)* | pinecone_diff_rag_mcp *(future)* |
|---------|-------------------|-------------------|----------------------|------------------|----------------------------------|
| **AI-Powered Chat** | ❌ Context endpoint only | ❌ | ✅ | ❌ | ❌ |
| **Answer Evaluation** | ❌ | ❌ | ✅ (paid plan, evaluate_answer) | ❌ | ❌ |
| **Delegation / Agentic Synthesis** | ❌ No chat API | ❌ | ✅ (assistant_chat) | ❌ | ❌ |
| **Document Retrieval** | ✅ Raw snippets only | ✅ With inference | ✅ Advanced | ✅ Advanced | ✅ Version-aware |
| **Version-Aware Retrieval** | ❌ | ❌ | ❌ | ❌ | ✅ (3-index architecture) |
| **Change-Only Search** | ❌ | ❌ | ❌ | ❌ | ✅ (diff index) |
| **Version Comparison** | ❌ | ❌ | ❌ | ❌ | ✅ (clause-level) |
| **Deduplication** | ❌ | ❌ | ❌ | ❌ | ✅ (~90% storage reduction) |
| **Negotiation Analysis** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Context Expansion (fetch_chunks)** | ❌ | ❌ | ❌ | ✅ (3 modes) | ❌ |
| **Web Document Manager UI** | ❌ | ❌ | ❌ | ✅ (PDF/DOCX/TXT/MD) | ✅ (PDF/DOCX/TXT/MD) |
| **Strategic Multi-Search** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **YAML Search Patterns** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **MCP Prompts** | ❌ | ❌ | ✅ (4 templates) | ✅ | ✅ |
| **Claude Skills** | ❌ | ❌ | ✅ (3 skills) | ✅ | ✅ |
| **Assistant Switching** | ❌ | N/A | ✅ | N/A | N/A |
| **Custom Embeddings** | ❌ | ❌ | ❌ | ✅ (4 providers) | ✅ (OpenAI-compatible) |
| **Local Embeddings** | ❌ | ❌ | ❌ | ✅ (Ollama) | ✅ (Ollama) |
| **Local Embeddings Prefix Support** | N/A | N/A | N/A | ✅ | ✅ |
| **Index Management** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Read-Only Safety** | ✅ | ❌ (has upsert) | ✅ | ✅ | ✅ |
| **Production Resilience** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Structured Citations** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Multi-Assistant** | ❌ | N/A | ✅ (5 assistants) | N/A | N/A |
| **Namespace Support** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Remote/HTTP Option** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Bulk Document Upload** | ❌ No scripts | ❌ No scripts | ✅ **Automated scripts** | ✅ **Automated scripts + Web UI** | ✅ **Automated scripts + Web UI** |
| **Document Processing** | ❌ Manual | ⚠️ Manual (tool only) | ✅ **Chunking + metadata** | ✅ **Chunking + metadata + embeddings** | ✅ **PDF/DOCX/OCR extraction chain** |
| **Free Tier Friendly** | ✅ | ✅ | ⚠️ (lifetime limits) | ✅ | ✅ (needs 3 of 5 free indexes) |
| **Automated Setup** | ✅ (Docker) | ✅ (NPM) | ✅ **Full deployment** | ✅ **Full deployment** | ✅ **Full deployment** |
| **Production Status** | ⚠️ Early Access | ⚠️ Early Access | ✅ Production | 🔜 Future Release | 🔜 Future Release |

---

## Document Upload & Population Workflows

This is a **critical differentiator** between the four implementations:

### Official Assistant MCP
**❌ NO document upload capability**
- Provides only retrieval from existing assistants
- You must manually create and populate assistants via:
  - **Pinecone web UI** (app.pinecone.io) - Drag-and-drop interface available ✅
  - Direct API calls with custom code
  - Third-party tools
- **Limitation:** Cannot automate document ingestion workflows
- **Mitigating factor:** Assistant web UI is user-friendly for manual uploads (small collections)

### Official Vector DB MCP
**⚠️ LIMITED document upload capability**
- Has `upsert-records` tool for adding individual records
- **BUT:** No automated bulk upload scripts for document collections
- **CRITICAL:** Vector databases have **NO web UI for document upload** ❌
  - Unlike Assistants, you can't drag-and-drop documents
  - Must upload pre-computed vectors via API
  - Web UI is only for viewing/managing, not uploading
- You must:
  - Write your own document processing code
  - Generate embeddings yourself (with Pinecone integrated inference)
  - Write your own chunking logic
  - Write your own metadata extraction
  - Write your own upload orchestration
  - Handle rate limiting manually
- **Good for:** Adding a few records at a time via MCP tools
- **Not good for:** Bulk uploading document libraries
- **Major limitation:** Without upload scripts, this MCP is **much harder to use** than the official Assistant MCP because there's no web UI fallback

### pinecone_assistant_mcp (This Repo)
**✅ FULL automated document upload**

**Included scripts:**
- `deploy/upload_files.py` - Upload documents to Pinecone Assistant
- Automatic chunking (configurable size and overlap)
- Metadata extraction and assignment
- Rate limiting and retry logic
- Progress tracking with estimates
- Post-upload verification

**Example usage:**
```bash
cd deploy
uv run python upload_files.py \
  --api-key "pcsk_YOUR_KEY" \
  --assistant-name "my-assistant" \
  --use-uspto-metadata  # or omit for generic metadata
```

**What it handles:**
- ✅ Automatic file discovery (.md, .txt files)
- ✅ USPTO-specific metadata extraction (or generic fallback)
- ✅ File size validation (10MB limits)
- ✅ Chunking for optimal retrieval
- ✅ Batch upload with rate limiting
- ✅ Progress bars and time estimates
- ✅ Upload verification
- ✅ Detailed success/failure reporting

**Reference implementation:**
- Includes USPTO MPEP documents
- Pre-configured metadata schemas
- System prompt configuration
- Complete end-to-end workflow

### pinecone_diff_rag_mcp *(Future Release)*
**✅ FULL automated document ingestion via MCP App web UI**

**Document ingestion methods:**
- **MCP App Web UI** (`http://localhost:8888`): Drag-and-drop PDF, DOCX, DOC, TXT, MD — auto-starts with server
- **`ingest_document` tool**: Ingest from text string (any MCP client)
- **`ingest_document_from_file` tool**: Ingest from local file path (.txt/.md only — binary formats use the web UI)

**What the extraction chain handles:**
- ✅ PDF: PyPDF2 (native) → Docling (free local Docker) → Mistral OCR (cloud, last resort)
- ✅ DOCX: python-docx → Docling fallback
- ✅ DOC: Docling (requires LibreOffice conversion if unavailable)
- ✅ TXT/MD: Direct read
- ✅ Smart version detection from filename (`contract_v1.pdf` → `doc_id="contract"`, `version="1.0"`)
- ✅ Automatic diff computation on each new version (vs. `previous_version`)
- ✅ Deduplication via content hash — unchanged clauses not re-stored

### pinecone_rag_mcp
**✅ FULL automated document upload**

**Included scripts:**
- `deploy/upload-documents.ts` - TypeScript upload with custom embeddings
- `deploy/upload-uspto-docs.js` - USPTO-specific upload
- `deploy/add-uspto-documents.js` - Add new USPTO documents

**Example usage:**
```bash
# Generic upload with any embedding provider
tsx deploy/upload-documents.ts <PINECONE_KEY> <INDEX_NAME> ./documents \
  --embedding openai \
  --embedding-key sk-XXX \
  --namespace your-domain

# USPTO-specific upload
node deploy/upload-uspto-docs.js <PINECONE_KEY> uspto-data
```

**What it handles:**
- ✅ Quad provider support (Ollama/OpenAI/Cohere/Pinecone)
- ✅ Automatic file discovery and processing
- ✅ Configurable chunking (2000 tokens, 175 overlap)
- ✅ Embedding generation with chosen provider
- ✅ Batch upload with NDJSON format
- ✅ Rate limiting (90 records/batch, 1s delay)
- ✅ Retry logic with exponential backoff
- ✅ Progress tracking
- ✅ Metadata assignment per chunk

**Reference implementation:**
- Includes USPTO MPEP documents
- Pre-configured for patent law corpus
- Windows PowerShell integration
- Automatic extraction and cleanup

---

## Key Takeaway: Document Population

**If you need to bulk upload documents:**
→ Choose **pinecone_assistant_mcp** or **pinecone_rag_mcp**

**If you already have populated assistants/indexes:**
→ Official MCPs work fine for retrieval

**Important distinction:**
- **Assistants:** Can manually upload via web UI if needed (drag-and-drop) ✅
- **Vector Databases:** **NO web UI for uploads** - MUST use API/scripts ❌
  - This makes upload scripts **essential** for vector database MCPs
  - Official Vector DB MCP without bulk upload scripts is significantly harder to use
  - pinecone_rag_mcp with automated upload scripts is **ready to use out of the box**

**Bottom line:** The official Pinecone MCPs assume you've already populated your data. The john-walkoe MCPs provide complete end-to-end workflows including automated document ingestion. This is especially critical for vector databases where there's no web UI upload option.

---

## Cost Comparison

### Official Assistant MCP
- **Free Tier:** Same as pinecone_assistant_mcp (lifetime limits)
- **Paid Plans:** Not available (early access)

### Official Vector DB MCP
- **Free Tier:** Same as pinecone_rag_mcp (monthly resetting limits)
- **Paid Plans:** Not available (early access)
- **Storage:** $0.116/GB/month (serverless)
- **Embeddings:** Pinecone integrated inference pricing

### pinecone_assistant_mcp
**Free Tier (Starter Plan):**
- ⚠️ **Token limits are LIFETIME PER PROJECT (do NOT reset monthly):**
  - Context: 500K tokens total
  - Input: 1.5M tokens total
  - Output: 200K tokens total
- Storage: 1GB (monthly reset)
- 5 assistants, 100 files per assistant
- **Once exhausted:** Must upgrade or delete/recreate project

**Paid Plans:**
- **Standard:** $50/month minimum
  - $0.05/hour per assistant (~$36/month for 1 assistant 24/7)
  - Input: $8/million tokens
  - Output: $15/million tokens
  - Context: $5/million tokens
  - Storage: $3/GB/month
- **Enterprise:** $500/month minimum + usage

**Monthly cost estimate (Standard plan, moderate usage):**
- 1 assistant 24/7: $36 (hourly)
- 5M input tokens: $40
- 1M output tokens: $15
- 2GB storage: $6
- **Total: ~$97/month**

### pinecone_diff_rag_mcp *(Future Release)*
**Free Tier (Starter Plan):**
- ⚠️ **Requires 3 of your 5 free serverless indexes** (content, version, diff)
- ✅ Operation limits **RESET MONTHLY** (same as standard Vector DB pricing)
- Read units: ~333K/month per index (1M total shared across all 5 indexes)
- Write units: ~666K/month per index (2M total shared)
- Storage: 2GB max total across all indexes
- **Embedding options:**
  - **Ollama:** $0 (run locally, unlimited)
  - **OpenAI:** ~$0.13/million tokens (text-embedding-3-small)
- **OCR (optional):** Mistral: $0.001/page (only needed for scanned PDFs without Docling)
- **Reranking (optional):** Cohere: pay-per-use

**Paid Plans (Standard):**
- **$50/month minimum** (same as other Vector DB-based MCPs)
- No hourly charges (unlike Assistant API)
- 3 indexes × storage cost
- LLM costs for `classify_and_search` and `analyze_negotiation_patterns` (OpenAI or Ollama)
- Ollama embeddings: $0 (local)

**Monthly cost estimate (Standard plan, moderate usage with Ollama):**
- 3 Pinecone indexes storage (2GB total): ~$0.23
- LLM for intent classification (gpt-4o-mini, ~1K queries): ~$0.30
- Embeddings (Ollama): $0
- Read/write units: ~$15–25
- **Total: ~$15–25/month** (vs. ~$97 for Assistant API)

### pinecone_rag_mcp
**Free Tier (Starter Plan):**
- ✅ **Operation limits RESET MONTHLY (unlike Assistant API):**
  - Read units: 1,000,000/month (query, fetch, list)
  - Write units: 2,000,000/month (upsert, update, delete)
  - Storage: 2GB max per project
- 5 serverless indexes (all in us-east-1)
- **Embedding options:**
  - **Ollama:** $0 (run locally, unlimited)
  - **Pinecone Inference:** $0.16/million tokens, 5M free/month
  - **OpenAI:** ~$0.13/million tokens (text-embedding-3-small)
  - **Cohere:** Free trial, then pay-per-use

**Paid Plans (Standard):**
- **$50/month minimum**
- **Read/Write Units:** Unlimited (pay for usage)
  - Read unit pricing: ~$0.116 per GB queried
  - Write unit pricing: Based on data size
- **Storage:** $0.116/GB/month (serverless)
- **Embeddings:** Varies by provider
  - Ollama: $0 (local)
  - Pinecone: $0.16/million tokens (unlimited on paid plans)
  - OpenAI: Pay OpenAI directly
  - Cohere: Pay Cohere directly
- **No hourly charges** (unlike Assistant API)

**Monthly cost estimate (Standard plan, moderate usage with Ollama):**
- Read units: ~$10 (varies by query volume)
- Write units: ~$5 (varies by upsert volume)
- Storage (2GB): $0.23
- Embeddings (Ollama): $0
- **Total: ~$15-20/month** (vs. ~$97 for Assistant API)

**Cost Optimization:**
- ✅ Use Ollama for $0 embeddings (completely free, unlimited)
- ✅ Free tier limits reset monthly (vs. lifetime for Assistant)
- ✅ No hourly assistant charges
- ✅ Can stay on free tier longer for moderate usage

---

## Technical Architecture

### Official Assistant MCP
- **Language:** TypeScript
- **Transport:** Streamable HTTP or stdio (Docker)
- **Deployment:** Remote endpoint or local Docker container
- **Dependencies:** Node.js or Docker

### Official Vector DB MCP
- **Language:** TypeScript
- **Transport:** stdio
- **Deployment:** NPM package
- **Dependencies:** Node.js 18+

### pinecone_assistant_mcp
- **Language:** Python 3.11+
- **Transport:** stdio
- **Package Manager:** uv
- **Deployment:** Local Python environment
- **Security:** Windows DPAPI, secure logging, input validation
- **Resilience:** Circuit breaker, retry with backoff, caching, bulkhead

### pinecone_rag_mcp
- **Language:** TypeScript
- **Transport:** stdio
- **Deployment:** NPM package (local Node.js)
- **Dependencies:** Node.js 18+
- **Embedding Clients:** OpenAI SDK, Cohere SDK, Pinecone SDK, Ollama HTTP

### pinecone_diff_rag_mcp *(Future Release)*
- **Language:** Python 3.11+
- **Framework:** FastMCP + FastAPI (MCP App web UI)
- **Transport:** stdio
- **Package Manager:** uv
- **Deployment:** Local Python environment
- **Indexes:** 3 Pinecone serverless indexes (content, version, diff)
- **Metadata Cache:** SQLite (ephemeral, synced from Pinecone)
- **Embedding:** OpenAI-compatible (OpenAI, Ollama, OpenRouter)
- **OCR Chain:** PyPDF2 → Docling (local Docker) → Mistral OCR (cloud)
- **Optional:** Cohere reranking, Docling GPU support

---

## Summary Recommendations

### For Simple Document Retrieval
→ **Official Assistant MCP** (if remote is acceptable) or **pinecone_rag_mcp** (if local preferred)

### For AI-Powered Research & Analysis
→ **pinecone_assistant_mcp** (only option exposing the Pinecone chat API with strategic search)

### For Agentic Workflows / Claude Context Window Preservation
→ **pinecone_assistant_mcp** — `assistant_chat` delegates synthesis to Pinecone AI; Claude receives compact answers (~500–2000 tokens) instead of raw document chunks, leaving Claude's context window free for orchestration. **The Official Assistant MCP cannot do this** — it calls the context endpoint only, never invoking the Pinecone AI model.

### For Index Management & Development
→ **Official Vector DB MCP** (official Pinecone support)

### For Custom Embedding Workflows *(Future)*
→ **pinecone_rag_mcp** (quad provider support: Ollama/OpenAI/Cohere/Pinecone)

### For Context Expansion / Agentic RAG *(Future)*
→ **pinecone_rag_mcp** — `fetch_chunks` retrieves chunks by ID, metadata filter, or prefix directly from Pinecone without re-embedding. Enables neighbor expansion (fetch adjacent chunks), section expansion (fetch a chunk ID range), and full document expansion (fetch all chunks by doc_id metadata). Use after `semantic_search` returns candidate chunks to give the agent the structural context it needs for accurate answers. (Based on [The AI Automators' research](https://www.youtube.com/watch?v=y72TrpffdSk))

### For Production Deployments
→ **pinecone_assistant_mcp** (resilience features)

### For Free Tier Maximization *(Future)*
→ **pinecone_rag_mcp** with Ollama embeddings ($0 cost) or Pinecone embeddings (5M free/month)
→ **Critical:** Vector DB free tier limits RESET monthly, Assistant API limits do NOT

### For Multi-Assistant Workflows
→ **pinecone_assistant_mcp** (only option supporting assistant switching)

### For Local/Offline Use *(Future)*
→ **pinecone_rag_mcp** with Ollama embeddings (fully local operation)

### For Version-Aware Document Analysis *(Future)*
→ **pinecone_diff_rag_mcp** — the only MCP purpose-built for multi-version documents. Tracks what changed between contract/policy versions, identifies negotiation patterns, reconstructs historical versions, and searches only diff content without duplicate noise.

### For Contract Negotiation Intelligence *(Future)*
→ **pinecone_diff_rag_mcp** — `analyze_negotiation_patterns` identifies which party is making concessions and which is holding firm across a sequence of contract versions.

---

## References

- **Official Assistant MCP:** https://docs.pinecone.io/guides/assistant/use-an-assistant-mcp-server
- **Official Vector DB MCP:** https://docs.pinecone.io/guides/integrations/use-pinecone-mcp-server
- **pinecone_assistant_mcp:** https://github.com/john-walkoe/pinecone_assistant_mcp
- **pinecone_rag_mcp:** https://github.com/john-walkoe/pinecone_rag_mcp *(future release)*
- **pinecone_diff_rag_mcp:** https://github.com/john-walkoe/pinecone_diff_rag_mcp *(future release)*
- **Model Context Protocol:** https://modelcontextprotocol.io/
- **Pinecone Pricing:** https://docs.pinecone.io/guides/assistant/pricing-and-limits
- **VersionRAG Paper:** https://arxiv.org/abs/2510.08109 *(inspiration for diff-indexed approach)*
