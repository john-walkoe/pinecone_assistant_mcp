---
name: pinecone-assistant
description: Research any document knowledge base using the Pinecone Assistant MCP. Guides optimal tool selection, token budget management, query formulation, and multi-assistant workflows. Use when the pinecone_assistant MCP is connected and user asks to search, look up, find, or research topics in their documents. Triggers on phrases like "search the knowledge base", "look up in documents", "find information", "what does the assistant say about", "research using Pinecone", "search my documents", or any request to retrieve information from an indexed document corpus.
metadata:
  author: pinecone-assistant-mcp
  version: 1.1.0
  mcp-server: pinecone_assistant
  category: knowledge-base-research
---

# Pinecone Assistant MCP - Research Skill

## Available Tools

| Tool | Cost Tier | Best For |
|------|-----------|----------|
| `assistant_context` | Context tokens (cheapest) | Raw document retrieval, most queries |
| `assistant_strategic_multi_search_context` | Context tokens | Multi-angle research, comprehensive coverage |
| `assistant_strategic_multi_search_chat` | Input tokens (expensive) | When AI synthesis across patterns is needed |
| `assistant_chat` | Input + output tokens (most expensive) | Complex follow-up, AI-powered analysis |
| `get_configuration_status` | Free | Check current assistant name and model |
| `update_configuration` | Free | Switch between assistants mid-conversation |

## Tool Selection Decision Tree

**Always start with the cheapest tool that meets the need:**

```
User wants to find information
├── Simple lookup / single topic
│   └── assistant_context (top_k=3-5)
│
├── Multi-angle / comprehensive topic
│   └── assistant_strategic_multi_search_context (context tokens)
│       └── Follow up with assistant_context for specific gaps
│
├── Need AI to reason across multiple search results
│   └── assistant_strategic_multi_search_chat (input tokens)
│       └── Only when synthesis/reasoning is explicitly needed
│
└── Complex conversation / targeted follow-up
    └── assistant_chat (most expensive - use last)
        └── Stateless by default - only add history when new
            question contains pronouns referencing prior answer
```

**Never start with `assistant_chat` when `assistant_context` would suffice.**

## Token Budget Management

### Free Tier Limits (LIFETIME — do NOT reset monthly)
- **Context tokens**: 500K lifetime — used by `assistant_context` and `*_context` variants
- **Input tokens**: 1.5M lifetime — used by `assistant_chat` and `assistant_strategic_multi_search_chat`
- **Output tokens**: 200K lifetime

⚠️ These are one-time lifetime allocations, not monthly quotas. Once exhausted, upgrade to a paid plan.

### Strategy
Maximize context token usage. Minimize input token usage.

| Tool | Approx. Cost Per Call | Lifetime Capacity (free tier) |
|------|----------------------|-------------------------------|
| `assistant_context` | ~5-10K context tokens | 50-100+ total queries |
| `assistant_strategic_multi_search_context` | ~10-20K context tokens | 25-50 total queries |
| `assistant_strategic_multi_search_chat` | ~30K input tokens | 50 total queries |
| `assistant_chat` (stateless) | ~30K input tokens | 50 total queries |
| `assistant_chat` (with 4-turn history) | ~130K input tokens | ~11 total queries |

### Multi-Turn Conversation Warning
The API is **stateless** — it has no memory between calls.

**Include history ONLY if** the new question contains explicit references like "that", "this", "it", "as mentioned", "the above", or "previously discussed".

**Default: send single-message queries (stateless).** Adding unnecessary history costs 4x more tokens per turn.

## Parameter Reference

### `assistant_context`
```
query                  (required unless messages provided) - What to search for
top_k                  - Snippets to return (default: 5, range: 1-64)
                       - 3 for quick lookup, 5-8 for comprehensive
snippet_size           - Tokens per snippet (default: 2048, range: 512-8192)
                       - 1024 for quick reference, 2048 default, 4096 for deep reading
filter                 - Optional metadata filter object
multimodal             - Retrieve image context from PDFs (API default: true)
                       - Set false for text-only corpora to save context tokens
include_binary_content - Include base64 image data in response (API default: true)
                       - Set false to get image references without base64 payload;
                         reduces response size significantly when images aren't needed
messages               - Multi-turn messages array as alternative to query
                       - Format: [{"role": "user", "content": "..."}, ...]
                       - multimodal and include_binary_content are ignored when using messages
```

**PDF corpus guidance**:
- Text-only corpus (MD, TXT, JSON): pass `multimodal=false` — no images to retrieve, saves tokens
- PDF corpus, text + image context needed: use defaults (API auto-enables multimodal)
- PDF corpus, text only (skip images): `multimodal=false` or `include_binary_content=false`
- PDF corpus, need to analyse image content: leave defaults, base64 data is included

### `assistant_strategic_multi_search_context`
```
query        (required) - Primary research topic
domain       - Search pattern domain (default: first available domain)
             - Use get_configuration_status to see what domains are loaded
top_k        - Snippets per search pattern (default: 5)
snippet_size - Tokens per snippet (default: 2048)
max_searches - Limit patterns executed (default: all enabled)
             - 2 for targeted, 4+ for comprehensive
```

### `assistant_chat`
```
messages     (required) - Array of {role, content} objects
             - Keep minimal - only include history when needed
model        - AI model (default: gpt-4o)
             - Options: gpt-4o, gpt-4.1, o4-mini, claude-3-5-sonnet,
               claude-3-7-sonnet, claude-sonnet-4-5, gemini-2.5-pro
temperature  - 0.0 (precise/factual) to 2.0 (creative) — default: 0.2
include_highlights - Include source citations (default: true)
context_options    - Override retrieval: {"top_k": 3, "snippet_size": 1024}
```

### `update_configuration`
```
assistant_name  (required) - Name of assistant to switch to
model           - Change default model (optional)
assistant_host  - Override host URL (optional, auto-detected)
```

## Query Formulation

**Good queries are specific and descriptive:**

```
GOOD: "authentication token expiration handling best practices"
BAD:  "authentication"

GOOD: "database connection pooling configuration parameters"
BAD:  "database"

GOOD: "error handling retry logic exponential backoff"
BAD:  "errors"
```

**Include domain terminology** from the document corpus. If the documents use specific jargon, use it in queries.

**For targeted lookups**, include document section identifiers, rule numbers, or section names if known.

## Standard Research Workflows

### Quick Reference Lookup
When user needs a specific fact, definition, or rule:
```
1. assistant_context(query="[specific topic]", top_k=3, snippet_size=1024)
2. Present findings directly from retrieved snippets
```

### Comprehensive Topic Research
When user needs full coverage of a topic:
```
1. assistant_strategic_multi_search_context(query="[topic]", max_searches=3-4)
2. assistant_context(query="[specific gap identified]", top_k=3)
   (only if strategic search left gaps)
3. Synthesize findings from retrieved context
```

### AI-Synthesized Research
When user needs reasoning, comparison, or interpretation:
```
1. assistant_strategic_multi_search_chat(query="[topic]", domain="[domain]")
   OR
   assistant_chat(messages=[{role:"user", content:"[question]"}])
2. Follow up with assistant_context for additional specific lookups
```

### Multi-Assistant Research
When different assistants cover different content areas:
```
1. get_configuration_status() → confirm current assistant
2. assistant_context or assistant_strategic_multi_search_context (current assistant)
3. update_configuration(assistant_name="[other-assistant]")
4. Repeat research on new knowledge base
5. Synthesize findings across sources
```

## Multi-Assistant Setup

Up to 5 assistants on the free tier. Each assistant indexes up to 10 files (50 files total).

Switch mid-conversation without losing Claude's context:
```
update_configuration(assistant_name="specialized-assistant")
```

Changes persist for the session. Restart Claude to revert to the original configured assistant.

## Delegation Pattern (Paid Plans / Agentic Workflows)

`assistant_chat` is a **sub-agent delegation** mechanism — Pinecone handles both retrieval and synthesis internally, returning only the compact result to Claude. Delegation preserves Claude's context window at the cost of Pinecone LLM tokens.

Use `context_options` to control Pinecone's internal retrieval size:
```
context_options={"top_k": 3, "snippet_size": 1024}  # smaller context to LLM
context_options={"top_k": 5, "snippet_size": 2048}  # default
```

**Use the `delegated_research` prompt** for a guided workflow with chaining patterns.

## Available Prompts

This MCP exposes four corpus-neutral prompts selectable from the prompt menu:

| Prompt | Parameters | Token tier | Use when |
|--------|-----------|-----------|---------|
| `deep_research` | `topic`, `domain?` | Context only | Thorough multi-angle coverage needed |
| `quick_lookup` | `topic` | Context only | Fast single-fact retrieval |
| `comparative_research` | `topic_a`, `topic_b` | Context only | Side-by-side comparison |
| `delegated_research` | `research_question`, `model?`, `prior_context?` | Context + LLM | Paid plan / agentic synthesis |

## Common Patterns

### When corpus is text-only (no PDFs)
- Pass `multimodal=false` to skip image retrieval and save context tokens:
  `assistant_context(query="...", multimodal=false)`

### When corpus contains PDFs with diagrams or figures
- Default behaviour retrieves both text and image context — no params needed
- To retrieve text context only (skip base64 image data):
  `assistant_context(query="...", include_binary_content=false)`
- To retrieve and analyse image content, use defaults (base64 included automatically)

### When search returns too many broad results
- Add more specific terms to the query
- Reduce `max_searches` to 2
- Switch from strategic multi-search to targeted `assistant_context`

### When search returns too few relevant results
- Broaden query terminology
- Increase `top_k` to 8-10
- Try a different domain if strategic search is being used

### When context limit is approaching
- Switch to more targeted `assistant_context` calls instead of multi-search
- Reduce `snippet_size` to 1024
- Use `max_searches: 2` to limit strategic search scope

### When switching knowledge bases
```
update_configuration(assistant_name="[new-assistant]")
```
