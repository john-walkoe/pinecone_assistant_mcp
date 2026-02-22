"""
MCP Prompt templates for the Pinecone Assistant MCP server.

Prompts are corpus-neutral — they work with any document knowledge base.
Each prompt is a workflow guide that Claude follows using the available tools.

Available prompts:
- deep_research:          Comprehensive multi-angle research (context tokens only)
- quick_lookup:           Fast single-topic reference lookup (context tokens only)
- comparative_research:   Side-by-side comparison of two topics (context tokens only)
- delegated_research:     Delegate to Pinecone AI for synthesis (paid plan / agentic)
"""

from mcp.types import (
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
    TextContent,
)

# ---------------------------------------------------------------------------
# Prompt registry — returned by list_prompts()
# ---------------------------------------------------------------------------

PROMPTS: list[Prompt] = [
    Prompt(
        name="deep_research",
        description=(
            "Comprehensive multi-angle research on any topic using token-efficient "
            "strategic context search. Executes multiple search patterns then fills "
            "gaps with targeted lookups. Uses context tokens only — no AI synthesis "
            "cost. Use when thorough coverage is needed. Trigger phrases: 'research "
            "thoroughly', 'comprehensive overview', 'deep dive', 'full coverage'."
        ),
        arguments=[
            PromptArgument(
                name="topic",
                description="Topic, question, or subject to research comprehensively",
                required=True,
            ),
            PromptArgument(
                name="domain",
                description=(
                    "Optional domain name to focus strategic search patterns "
                    "(must match a domain configured in strategic-searches.yaml). "
                    "Leave blank to use the default domain."
                ),
                required=False,
            ),
        ],
    ),
    Prompt(
        name="quick_lookup",
        description=(
            "Fast, token-efficient single-topic lookup. Returns targeted context "
            "snippets for a specific fact, definition, rule, or reference. Minimal "
            "token cost — context tier only, single tool call. Trigger phrases: "
            "'look up', 'what is', 'find', 'quick reference', 'definition of'."
        ),
        arguments=[
            PromptArgument(
                name="topic",
                description="Specific term, rule, concept, or question to look up",
                required=True,
            ),
        ],
    ),
    Prompt(
        name="comparative_research",
        description=(
            "Research two topics from the knowledge base and present a structured "
            "comparison covering attributes, similarities, differences, and when to "
            "apply each. Uses context tokens only — two sequential lookups. "
            "Trigger phrases: 'compare', 'difference between', 'vs', 'contrast'."
        ),
        arguments=[
            PromptArgument(
                name="topic_a",
                description="First topic to research and compare",
                required=True,
            ),
            PromptArgument(
                name="topic_b",
                description="Second topic to research and compare",
                required=True,
            ),
        ],
    ),
    Prompt(
        name="delegated_research",
        description=(
            "Delegate research to the Pinecone Assistant AI for synthesized, "
            "citation-backed responses. The assistant handles both internal context "
            "retrieval AND synthesis — Claude receives only the compact result, "
            "preserving Claude's context window for orchestration. "
            "WARNING: Uses both Pinecone context tokens AND LLM input tokens "
            "(Pinecone internally sends ~10-32K tokens to the LLM per call). "
            "Best for paid Pinecone plans or agentic workflows where Claude's "
            "context window is the primary constraint. Trigger phrases: "
            "'delegate to assistant', 'let the assistant research', "
            "'assistant synthesize', 'agentic research', 'paid plan research'."
        ),
        arguments=[
            PromptArgument(
                name="research_question",
                description="Research question or task to delegate to the Pinecone Assistant AI",
                required=True,
            ),
            PromptArgument(
                name="model",
                description=(
                    "AI model for synthesis. Default: gpt-4o. "
                    "Options: gpt-4o, gpt-4.1, o4-mini, claude-3-5-sonnet, "
                    "claude-3-7-sonnet, claude-sonnet-4-5, gemini-2.5-pro"
                ),
                required=False,
            ),
            PromptArgument(
                name="prior_context",
                description=(
                    "Optional: paste the prior assistant answer here to include as "
                    "conversation context for a follow-up question. Only use when "
                    "the new question explicitly references the previous answer."
                ),
                required=False,
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Prompt content builders — called by get_prompt()
# ---------------------------------------------------------------------------

def _deep_research(args: dict[str, str]) -> GetPromptResult:
    topic = args.get("topic", "")
    domain = args.get("domain", "")
    domain_line = f'\n    domain="{domain}",' if domain else ""

    content = f"""# DEEP RESEARCH: {topic}

Research "{topic}" comprehensively using token-efficient context retrieval.

**Token strategy**: Use context tools only — no AI synthesis cost.

---

## Step 1: Strategic Multi-Search

Use the best available multi-angle retrieval tool (`assistant_strategic_multi_search_context`
preferred; fall back to `assistant_strategic_multi_search_chat` or multiple
`assistant_context` calls if multi-search is not available).

Use a **descriptive query** — expand "{topic}" with relevant terminology,
related concepts, or domain framing rather than using the bare label alone.
top_k=5, snippet_size=2048, max_searches=4{domain_line}

This retrieves raw document chunks across multiple research angles.

---

## Step 2: Identify Coverage Gaps

Review all retrieved snippets. Note any important sub-topics that were:
- Not returned at all
- Only superficially mentioned
- Mentioned but lacking detail

---

## Step 3: Targeted Follow-Up (for gaps only)

For each significant gap, run one targeted retrieval using the best available
context tool. Use a specific, descriptive query for the missing sub-topic —
not just a single keyword. Limit to 2-3 follow-up calls.
top_k=3, snippet_size=2048

---

## Step 4: Synthesize and Present

Compile all retrieved context into a structured response organized by:
1. Core definitions and concepts
2. Standards, requirements, or procedures
3. Key examples or precedents
4. Practical guidance or implications

Cite source document names and page references from the snippet metadata throughout.
"""

    return GetPromptResult(
        description=f"Comprehensive research on: {topic}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ],
    )


def _quick_lookup(args: dict[str, str]) -> GetPromptResult:
    topic = args.get("topic", "")

    content = f"""# QUICK LOOKUP: {topic}

Retrieve a fast, focused answer about "{topic}".

**Token target**: Under 5K context tokens — single tool call.

---

## Execute Lookup

Use the best available context retrieval tool (`assistant_context` preferred
for lowest cost; fall back to any available retrieval tool if needed).

Use a **descriptive query** — expand "{topic}" with relevant terminology or
context rather than passing the bare label. For example, if "{topic}" is a
short abbreviation or term, include the full form, related concepts, or the
governing rule/section.
top_k=3, snippet_size=1024

---

## Present Findings

From the retrieved snippets, provide:
- The relevant definition, rule, or information
- Source document reference
- Any important caveats or related items mentioned in the snippets

---

## If Results Are Irrelevant

Retry once with broader or rephrased terminology using the same retrieval tool.
top_k=3, snippet_size=1024

Do not execute additional searches beyond one retry. If still not found,
report what was retrieved and suggest a more specific query.
"""

    return GetPromptResult(
        description=f"Quick lookup: {topic}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ],
    )


def _comparative_research(args: dict[str, str]) -> GetPromptResult:
    topic_a = args.get("topic_a", "")
    topic_b = args.get("topic_b", "")

    content = f"""# COMPARATIVE RESEARCH: {topic_a} vs {topic_b}

Research both "{topic_a}" and "{topic_b}" from the knowledge base and present
a structured comparison.

**Token strategy**: Two sequential context retrievals — no AI synthesis cost.

---

## Step 1: Research "{topic_a}"

Use the best available Pinecone retrieval tool (prefer `assistant_context` for
lowest cost; fall back to `assistant_strategic_multi_search_context` or
`assistant_strategic_multi_search_chat` if needed).

Retrieve 4 snippets with a **descriptive query** — expand "{topic_a}" with
relevant terminology, section numbers, or legal/technical concepts rather than
using the bare label as the query. For example, instead of just "{topic_a}",
use a query like "{topic_a} [key definition, statutory basis, or core concept]".

top_k=4, snippet_size=2048

---

## Step 2: Research "{topic_b}"

Same approach as Step 1. Expand "{topic_b}" into a descriptive query that
includes the relevant terminology or framing from the knowledge base domain.

top_k=4, snippet_size=2048

---

## Step 3: Present Comparison

Structure the response as follows:

**{topic_a}**
- [Key attributes, definitions, and requirements from retrieved context]

**{topic_b}**
- [Key attributes, definitions, and requirements from retrieved context]

**Similarities**
- [What they share in common]

**Differences**
- [How they differ in purpose, application, or requirements]

**When to Apply Each**
- Use {topic_a} when: [specific conditions]
- Use {topic_b} when: [specific conditions]

**Interactions** (if applicable)
- [How they relate to or affect each other]

Cite source document names and references throughout.
"""

    return GetPromptResult(
        description=f"Comparison: {topic_a} vs {topic_b}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ],
    )


def _delegated_research(args: dict[str, str]) -> GetPromptResult:
    research_question = args.get("research_question", "")
    model = args.get("model", "gpt-4o")
    prior_context = args.get("prior_context", "")

    # Build messages array content
    if prior_context:
        messages_block = f"""messages=[
        {{"role": "user", "content": "[original question that produced the prior context]"}},
        {{"role": "assistant", "content": "{prior_context[:200]}..."}},
        {{"role": "user", "content": "{research_question}"}}
    ]"""
        history_note = (
            "Prior context provided — including it as conversation history "
            "because the new question references prior content."
        )
    else:
        messages_block = f"""messages=[
        {{"role": "user", "content": "{research_question}"}}
    ]"""
        history_note = (
            "No prior context — sending as a stateless query (most token-efficient)."
        )

    content = f"""# DELEGATED RESEARCH: {research_question}

## Execute Delegation

{history_note}

```
assistant_chat(
    {messages_block},
    model="{model}",
    temperature=0.2,
    include_highlights=True,
    context_options={{"top_k": 5, "snippet_size": 2048}}
)
```

**Reduce Pinecone's internal context cost** by lowering `context_options`:
```
context_options={{"top_k": 3, "snippet_size": 1024}}  # ~3K tokens to LLM (vs ~32K default)
```

---

## Process the Response

The assistant returns:
- `message.content` — Synthesized answer, ready to use directly
- `citations` — Source documents with page references (validate key claims here)
- `usage.prompt_tokens` — Reflects Pinecone's internal context size sent to LLM

Use `message.content` as the research result. Do not re-summarize it unless
the user asks for further analysis — the assistant has already synthesized it.

---

## Chaining Multiple Delegations (Agentic Pattern)

For multi-part research tasks, chain independent calls without history:

```
# Independent questions — no history, most efficient
assistant_chat(messages=[{{"role": "user", "content": "First research question"}}])
assistant_chat(messages=[{{"role": "user", "content": "Second research question"}}])

# Follow-up that references prior answer — include history ONLY in this case
assistant_chat(messages=[
    {{"role": "user", "content": "First question"}},
    {{"role": "assistant", "content": "[prior answer]"}},
    {{"role": "user", "content": "Follow-up referencing 'that' or 'the above'"}}
])
```

**Rule**: Default to stateless (no history). Add history only when the new
question contains explicit back-references: "that", "this", "as mentioned",
"the above", "previously discussed".
"""

    return GetPromptResult(
        description=f"Delegated research: {research_question}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ],
    )


# ---------------------------------------------------------------------------
# Public dispatch function — called by server.get_prompt()
# ---------------------------------------------------------------------------

def get_prompt_result(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Dispatch prompt name to its builder function."""
    args = arguments or {}

    if name == "deep_research":
        return _deep_research(args)
    elif name == "quick_lookup":
        return _quick_lookup(args)
    elif name == "comparative_research":
        return _comparative_research(args)
    elif name == "delegated_research":
        return _delegated_research(args)
    else:
        raise ValueError(f"Unknown prompt: '{name}'")
