---
name: pinecone-assistant-paid-plan
description: Delegation and answer evaluation workflows for the Pinecone Assistant. Uses assistant_chat as a sub-agent (Pinecone handles retrieval and synthesis internally) and evaluate_answer to validate answer correctness and completeness against ground truth. Use when Claude's context window is the primary constraint or when agentic research workflows are needed. Triggers on "delegate to the assistant", "let Pinecone synthesize", "agentic research", "evaluate answer quality", "validate the answer", "check correctness", "score my answer", "context window is full", "chain multiple research tasks", or explicit preference to offload synthesis.
metadata:
  author: pinecone-assistant-mcp
  version: 2.0.0
  mcp-server: pinecone_assistant
  category: knowledge-base-research
  base-skill: pinecone-assistant
  tier: paid
---

# Pinecone Assistant MCP - Paid Plan Skill

`assistant_chat` is a sub-agent delegation mechanism. Pinecone internally retrieves context from the knowledge base, feeds it to the configured LLM, and returns a synthesized, citation-backed answer. Claude receives only the compact result (~500–2000 tokens) rather than raw document chunks.

`evaluate_answer` is a quality gate. Given a question, a generated answer, and a ground truth answer, it scores correctness (precision), completeness (recall), and alignment (harmonic mean) — and returns per-fact entailment reasoning.

**Primary tools**: `assistant_chat`, `evaluate_answer`
**Primary prompt**: `delegated_research`

## Available Tools

| Tool | Cost Tier | Best For |
|------|-----------|----------|
| `assistant_context` | Context tokens (cheapest) | Raw document retrieval, targeted lookups |
| `assistant_strategic_multi_search_context` | Context tokens | Multi-angle raw retrieval, comprehensive coverage |
| `assistant_strategic_multi_search_chat` | Input tokens | AI synthesis across multiple search patterns |
| `assistant_chat` | Input + output tokens | Delegated synthesis — Pinecone AI handles retrieval + answer |
| `evaluate_answer` | Input + output tokens | Score answer correctness, completeness, and alignment |
| `get_configuration_status` | Free | Check current assistant name and model |
| `update_configuration` | Free | Switch between assistants mid-conversation |

## Tool Selection Decision Tree

Choose based on the task:

```
User wants to find information
├── Need synthesized answer + citations (let Pinecone do the work)
│   └── assistant_chat (context_options={"top_k": 5, "snippet_size": 2048})
│       └── delegated_research prompt for guided workflow
│
├── Need to validate answer quality against known ground truth
│   └── evaluate_answer(question, answer, ground_truth_answer)
│       ├── Scores: correctness (precision), completeness (recall), alignment (F1)
│       └── Use after assistant_chat in agentic/evaluation workflows
│
├── Claude's context window under pressure
│   └── assistant_chat (delegation preserves context window)
│       └── Chain independent calls without history
│
├── Need raw chunks to synthesize yourself / control the output
│   ├── Single topic → assistant_context (top_k=3-5)
│   └── Multi-angle → assistant_strategic_multi_search_context
│
└── Need AI to reason across many search patterns
    └── assistant_strategic_multi_search_chat
```

Stateless by default for all `assistant_chat` calls — add history only when the new question contains explicit back-references.

## Parameter Reference

### `assistant_chat`
```
messages         (required) - Array of {role, content} objects
                 - Default: single-message stateless query
model            - AI model (default: gpt-4o)
                 - Options: gpt-4o, gpt-4.1, o4-mini, claude-3-5-sonnet,
                   claude-3-7-sonnet, claude-sonnet-4-5, gemini-2.5-pro
temperature      - 0.0 (precise/factual) to 2.0 (creative) — default: 0.2
include_highlights   - Source citations (default: true)
context_options  - Override Pinecone's internal retrieval:
                   {"top_k": 3, "snippet_size": 1024}  # ~3K tokens to LLM
                   {"top_k": 5, "snippet_size": 2048}  # ~10K tokens (recommended)
                   {"top_k": 16, "snippet_size": 2048} # ~32K tokens (max)
```

### `evaluate_answer`
```
question             (required) - The question the answer was generated for
answer               (required) - The answer to evaluate (typically from assistant_chat)
ground_truth_answer  (required) - The known correct reference answer

Returns:
  metrics.correctness  - Precision: how much of the answer is factually correct (0.0–1.0)
  metrics.completeness - Recall: how much of the ground truth the answer covers (0.0–1.0)
  metrics.alignment    - Harmonic mean of correctness + completeness (F1 score, 0.0–1.0)
  reasoning.evaluated_facts - Per-fact entailment: "entailed" | "contradicted" | "neutral"
  usage                - prompt_tokens, completion_tokens, total_tokens
```

**Entailment values**:
- `entailed` ✅ — fact from ground truth is supported by the answer
- `contradicted` ❌ — fact from ground truth is contradicted by the answer
- `neutral` ➖ — fact is neither supported nor contradicted (answer is silent on it)

### `assistant_context`
```
query        (required unless messages provided) - What to search for
top_k        - Snippets to return (default: 5, range: 1-64)
             - 3 for quick lookup, 5-8 for comprehensive
snippet_size - Tokens per snippet (default: 2048, range: 512-8192)
filter       - Optional metadata filter object
multimodal             - Retrieve image context from PDFs (API default: true, query-only)
                       - Set false for text-only corpora to save context tokens
include_binary_content - Include base64 image data (API default: true, query-only)
                       - Set false to reduce response size when image analysis not needed
messages               - Multi-turn messages as alternative to query
                       - multimodal and include_binary_content are ignored when using messages
```

### `assistant_strategic_multi_search_context`
```
query        (required) - Primary research topic
domain       - Search pattern domain (default: first available domain)
top_k        - Snippets per search pattern (default: 5)
snippet_size - Tokens per snippet (default: 2048)
max_searches - Limit patterns executed (default: all enabled)
             - 2 for targeted, 4+ for comprehensive
```

### `update_configuration`
```
assistant_name  (required) - Name of assistant to switch to
model           - Change default model (optional)
assistant_host  - Override host URL (optional, auto-detected)
```

## Alignment Score Interpretation

| Score Range | Interpretation | Recommended Action |
|-------------|---------------|-------------------|
| 0.85–1.0 | Excellent — answer is accurate and complete | Present directly |
| 0.70–0.84 | Good — minor gaps or omissions | Present with note of limitations |
| 0.50–0.69 | Fair — significant gaps; some facts missing or wrong | Retry with more context (`top_k` ↑) |
| 0.0–0.49 | Poor — answer is substantially incomplete or incorrect | Increase `context_options`, rephrase query, or switch model |

**When completeness is low but correctness is high**: The answer is accurate but incomplete — increase `top_k` to retrieve more document coverage.

**When correctness is low**: The answer contains hallucinations or errors — inspect `contradicted` facts in `evaluated_facts` to understand what went wrong.

## Research Workflows

### Delegated Synthesis
When user wants a synthesized answer with citations:
```
1. assistant_chat(
     messages=[{"role": "user", "content": "[question]"}],
     model="gpt-4o",
     temperature=0.2,
     include_highlights=True,
     context_options={"top_k": 5, "snippet_size": 2048}
   )
2. Present message.content directly — do not re-summarize
```

### Comprehensive Delegated Research
When topic requires broad coverage:
```
1. assistant_chat(messages=[{"role": "user", "content": "[broad topic overview]"}],
     context_options={"top_k": 10, "snippet_size": 2048})
2. assistant_context(query="[specific gap]", top_k=3)  # targeted follow-up
```

### Quick Targeted Lookup
When user needs a specific fact (context-only, cheapest):
```
1. assistant_context(query="[specific topic]", top_k=3, snippet_size=1024)
2. Present findings from retrieved snippets
```

### Multi-Assistant Research
When different assistants cover different content areas:
```
1. get_configuration_status() → confirm current assistant
2. assistant_chat or assistant_context (current assistant)
3. update_configuration(assistant_name="[other-assistant]")
4. Repeat research on new knowledge base
5. Synthesize findings across sources
```

## Answer Quality Evaluation Workflows

### Single Answer Validation
When you have a generated answer and a known ground truth to check against:
```
1. answer = assistant_chat(
     messages=[{"role": "user", "content": "[question]"}],
     context_options={"top_k": 5, "snippet_size": 2048}
   )

2. result = evaluate_answer(
     question="[same question]",
     answer=answer.message.content,
     ground_truth_answer="[known correct answer]"
   )

3. If result.metrics.alignment >= 0.70: present answer
   Else: see Iterative Refinement workflow below
```

### Iterative Refinement (Quality Gate)
When answer quality may be insufficient and you need to improve it:
```
1. answer = assistant_chat(
     messages=[{"role": "user", "content": "[question]"}],
     context_options={"top_k": 5, "snippet_size": 2048}
   )

2. scores = evaluate_answer(
     question="[question]",
     answer=answer.message.content,
     ground_truth_answer="[reference answer]"
   )

3. If scores.metrics.alignment < 0.70:
   a. Inspect evaluated_facts for "contradicted" or "neutral" facts
   b. Identify what's missing — increase context or refine query
   c. Retry: assistant_chat(
        messages=[{"role": "user", "content": "[rephrased question]"}],
        context_options={"top_k": 10, "snippet_size": 2048}  # more context
      )
   d. Re-evaluate to confirm improvement

4. Present final answer with alignment score if user asked for quality info
```

**Stop condition**: 2 refinement attempts maximum. If alignment stays below 0.70 after retry, present the best answer obtained and note the limitation.

### RAG Evaluation (Batch Testing)
When you have a test set of question/ground-truth pairs and want to measure RAG quality:
```
For each (question, ground_truth_answer) in test_set:
  1. answer = assistant_chat(
       messages=[{"role": "user", "content": question}],
       context_options={"top_k": 5, "snippet_size": 2048}
     )
  2. scores = evaluate_answer(
       question=question,
       answer=answer.message.content,
       ground_truth_answer=ground_truth_answer
     )
  3. Record: correctness, completeness, alignment

Aggregate: mean alignment across all test cases
Report: which questions scored poorly (alignment < 0.70) for targeted improvement
```

### Agentic Pipeline with Quality Gate
When building multi-step agentic workflows where answer accuracy matters:
```
1. Retrieve: assistant_chat(messages=[{"role": "user", "content": "[step question]"}])
2. Validate: evaluate_answer(question, answer, ground_truth)
3. Gate: only proceed to next step if alignment >= threshold
4. Chain next step using validated answer as context
```

## Stateless by Default

The API has no memory between calls. **Send single-message queries unless the new question explicitly references the prior answer.**

```
# Default: stateless
assistant_chat(messages=[{"role": "user", "content": "Research question"}])

# With history — ONLY when question uses back-references ("that", "it", "the above")
assistant_chat(messages=[
    {"role": "user", "content": "First question"},
    {"role": "assistant", "content": "[prior answer]"},
    {"role": "user", "content": "Follow-up referencing the above"}
])
```

Adding 4 turns of history costs ~4× more tokens per call.

## Agentic Chaining Pattern

For multi-part research, chain independent calls without history:

```
result_a = assistant_chat(messages=[{"role": "user", "content": "First topic"}])
result_b = assistant_chat(messages=[{"role": "user", "content": "Second topic"}])
result_c = assistant_chat(messages=[{"role": "user", "content": "Third topic"}])

# Synthesize all three results in Claude's context
```

Each call is independent — no shared state, no accumulated history cost.

## context_options Tuning

| Setting | Tokens to LLM | Use when |
|---------|--------------|---------|
| `top_k=3, snippet_size=1024` | ~3K | Focused single-concept questions |
| `top_k=5, snippet_size=2048` | ~10K | Standard research (recommended) |
| `top_k=10, snippet_size=2048` | ~20K | Broad topic coverage |
| `top_k=16, snippet_size=2048` | ~32K | Maximum coverage (default if omitted) |

Start with `top_k=5, snippet_size=2048` and increase only if answers are incomplete or evaluation scores are low.

## Processing the Response

```
message.content      # Synthesized answer — use directly
citations            # Source documents with page references
usage.prompt_tokens  # Reflects Pinecone's internal context size sent to LLM
```

Use `message.content` directly. Validate key claims against `citations` rather than re-retrieving the same documents.

## Model Selection

| Model | Best for |
|-------|---------|
| `gpt-4o` | General research, balanced speed/quality (default) |
| `gpt-4.1` | When GPT-4o misses nuance |
| `o4-mini` | High-volume agentic tasks where cost matters |
| `claude-sonnet-4-5` | When Claude reasoning style is preferred |
| `gemini-2.5-pro` | Long-context synthesis across very large documents |

## Mixing Delegation with Context Retrieval

Delegation and direct retrieval are not mutually exclusive:

```
# Broad synthesis via delegation
overview = assistant_chat(messages=[{"role": "user", "content": "Overview of [topic]"}])

# Targeted follow-up via context retrieval (cheaper)
detail = assistant_context(query="[specific sub-topic from overview]", top_k=3)
```

Use `assistant_chat` for synthesis, `assistant_context` for filling specific gaps.

## Multi-Assistant Setup

Switch assistants mid-conversation without losing Claude's context:
```
update_configuration(assistant_name="specialized-assistant")
```

Changes persist for the session. Restart Claude to revert to the original configured assistant.

## Query Formulation

**Specific and descriptive queries return better results from the Pinecone AI:**

```
GOOD: "authentication token expiration handling best practices"
BAD:  "authentication"

GOOD: "database connection pooling configuration parameters"
BAD:  "database"
```

Include domain terminology, section identifiers, or rule numbers when known.

## Available Prompts

| Prompt | Parameters | Token tier | Use when |
|--------|-----------|-----------|---------|
| `deep_research` | `topic`, `domain?` | Context only | Thorough multi-angle raw retrieval |
| `quick_lookup` | `topic` | Context only | Fast single-fact retrieval |
| `comparative_research` | `topic_a`, `topic_b` | Context only | Side-by-side comparison |
| `delegated_research` | `research_question`, `model?`, `prior_context?` | Context + LLM | Delegated synthesis with chaining |

## Common Patterns

### When delegation returns incomplete or vague answers
- Increase `context_options` top_k: `{"top_k": 10, "snippet_size": 2048}`
- Switch to `assistant_context` and synthesize in Claude's context for full control
- If you have a reference answer, use `evaluate_answer` to quantify the gap

### When evaluate_answer alignment score is low
- **Low completeness, high correctness**: Answer is accurate but incomplete — increase `top_k`
- **Low correctness**: Check `contradicted` facts in `evaluated_facts` — consider switching model or rephrasing query
- **Both low**: The knowledge base may not contain sufficient information on the topic

### When you don't have a ground truth answer for evaluate_answer
- `evaluate_answer` requires a `ground_truth_answer` — it cannot evaluate without a reference
- For exploratory queries where no ground truth exists, use `assistant_context` to retrieve raw chunks and assess coverage manually
- For testing, derive ground truths from authoritative sections of your indexed documents

### When search returns too many broad results
- Add more specific terms to the query
- Switch from multi-search to targeted `assistant_context`

### When search returns too few relevant results
- Broaden query terminology
- Increase `top_k` to 8-10 in `assistant_context`

### When switching knowledge bases
```
update_configuration(assistant_name="[new-assistant]")
```
