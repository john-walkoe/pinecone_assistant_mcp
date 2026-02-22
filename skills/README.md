# Pinecone Assistant MCP - Claude Skills

Three Claude skills are included in this directory for guided research workflows in Claude Code and Claude.ai. Skills provide Claude with domain-specific instructions for tool selection, token optimization, and research patterns — without requiring you to explain the workflow each session.

## Available Skills

| Skill | Directory | Audience | Primary Tool |
|-------|-----------|----------|-------------|
| [`pinecone-assistant`](pinecone-assistant/SKILL.md) | `skills/pinecone-assistant/` | Any corpus | `assistant_context` |
| [`pinecone-assistant-uspto`](pinecone-assistant-uspto/SKILL.md) | `skills/pinecone-assistant-uspto/` | USPTO / MPEP | Domain-specific search |
| [`pinecone-assistant-paid-plan`](pinecone-assistant-paid-plan/SKILL.md) | `skills/pinecone-assistant-paid-plan/` | Paid plan / agentic | `assistant_chat` |

---

## Installation

### Claude Code (Claude CLI)

Copy the skill directory into your Claude skills folder:

```bash
# Copy individual skills (run from the pinecone_assistant_mcp directory)
cp -r skills/pinecone-assistant ~/.claude/skills/
cp -r skills/pinecone-assistant-uspto ~/.claude/skills/
cp -r skills/pinecone-assistant-paid-plan ~/.claude/skills/
```

**Windows (PowerShell):**
```powershell
# From the pinecone_assistant_mcp directory
Copy-Item -Recurse skills\pinecone-assistant $env:USERPROFILE\.claude\skills\
Copy-Item -Recurse skills\pinecone-assistant-uspto $env:USERPROFILE\.claude\skills\
Copy-Item -Recurse skills\pinecone-assistant-paid-plan $env:USERPROFILE\.claude\skills\
```

After copying, invoke the skill in Claude Code:
```
/pinecone-assistant
```

### Claude.ai (Web Interface)

Upload the SKILL.md file for the skill you want using the Claude.ai Projects feature or attach it as context at the start of a conversation.

---

## Skill Descriptions

### `pinecone-assistant` — Generic Corpus Research

**File**: `skills/pinecone-assistant/SKILL.md`

**Best for**: Any document corpus — legal, medical, technical, financial, or custom

**What it teaches Claude**:
- Tool selection decision tree (which tool to use and when)
- Token budget management for free-tier users
- Multi-assistant setup and switching with `update_configuration`
- Query formulation best practices
- Parameter reference for all 6 tools

**Tool priority** (cost-optimized):
1. `assistant_context` — single-topic retrieval (default first choice)
2. `assistant_strategic_multi_search_context` — multi-angle raw retrieval
3. `assistant_strategic_multi_search_chat` — AI synthesis across search patterns
4. `assistant_chat` — delegated synthesis (use sparingly on free tier)

**Key guidance**:
- Always try `assistant_context` before escalating to AI tools
- Stateless by default: only include conversation history when questions explicitly reference prior answers
- `top_k=5, snippet_size=2048` is the recommended default for `assistant_context`

**Triggers**: Generic document research, knowledge base lookup, tool selection questions

---

### `pinecone-assistant-uspto` — USPTO / MPEP Research

**File**: `skills/pinecone-assistant-uspto/SKILL.md`

**Best for**: Patent law research using the included USPTO corpus (MPEP, examination guidelines, training materials)

**What it teaches Claude** (extends `pinecone-assistant`):
- 11 pre-configured search domains with descriptions and use cases
- Domain selection guide mapping legal issue types to domains
- Core research workflows for §101, §103, §112, and PTAB proceedings
- Query patterns with MPEP section numbers and examination terminology
- Cross-MCP integration with PFW, FPD, and PTAB servers

**USPTO Search Domains**:

| Domain | Use When |
|--------|---------|
| `section_101_eligibility` | Patent eligibility (Alice, Mayo) rejections |
| `section_103_obviousness` | Obviousness rejections and combination of references |
| `section_112_requirements` | Written description, enablement, indefiniteness |
| `section_102_novelty` | Anticipation and novelty rejections |
| `claim_construction` | Claim interpretation and BRI |
| `ptab_procedures` | IPR, PGR, PTAB practice and procedure |
| `mechanical_patents` | Mechanical and structural inventions |
| `software_patents` | Software, algorithms, and computer-implemented inventions |
| `general_patent_law` | Broad patent law questions not fitting specific domains |

**Key workflows**:
- **Office Action Response**: Domain search → MPEP guidance → prosecution strategy
- **§101 Eligibility Analysis**: Alice/Mayo two-step framework research
- **§103 Obviousness**: TSM test, motivation to combine, objective indicia
- **PTAB Research**: IPR/PGR filing requirements, estoppel, trial procedures

**Triggers**: Patent law questions, MPEP lookups, office action research, USPTO examination procedure

---

### `pinecone-assistant-paid-plan` — Agentic Delegation + Answer Evaluation

**File**: `skills/pinecone-assistant-paid-plan/SKILL.md`

**Best for**: Users on a paid Pinecone plan, or agentic workflows where Claude's context window is the primary constraint

**What it teaches Claude** (extends `pinecone-assistant`):
- When to use `assistant_chat` as a sub-agent for delegation
- How to use `evaluate_answer` to score answer correctness, completeness, and alignment against a ground truth
- Iterative refinement loop: generate → evaluate → improve → re-evaluate
- RAG evaluation workflows for batch testing question/answer pairs
- `context_options` tuning for controlling Pinecone's internal retrieval
- Agentic chaining patterns for multi-part research
- Mixing delegation with context retrieval for cost efficiency
- Model selection guidance for different research tasks

**Primary tools**: `assistant_chat`, `evaluate_answer`

**Why delegation preserves context window**:
- Claude receives only the synthesized answer (~500–2000 tokens)
- Instead of raw document chunks (which can be 10–32K tokens per query)
- Pinecone handles retrieval and synthesis internally

**Answer evaluation**:

`evaluate_answer` scores a generated answer against a known ground truth:

| Metric | What it measures |
|--------|-----------------|
| `correctness` | Precision — how much of the answer is factually correct |
| `completeness` | Recall — how much of the ground truth the answer covers |
| `alignment` | Harmonic mean of correctness + completeness (F1 score) |

Per-fact entailment breakdown: `entailed` ✅ / `contradicted` ❌ / `neutral` ➖

**context_options tuning**:

| Setting | Tokens to LLM | Use When |
|---------|--------------|---------|
| `top_k=3, snippet_size=1024` | ~3K | Focused single-concept questions |
| `top_k=5, snippet_size=2048` | ~10K | Standard research (recommended) |
| `top_k=10, snippet_size=2048` | ~20K | Broad topic coverage |
| `top_k=16, snippet_size=2048` | ~32K | Maximum coverage |

**Agentic chaining pattern**:
```
# Chain independent calls without history — each is stateless
result_a = assistant_chat("First research question")
result_b = assistant_chat("Second research question")
result_c = assistant_chat("Third research question")

# Claude synthesizes the three compact answers
```

**Triggers**: "delegate to the assistant", "let Pinecone synthesize", "agentic research", "evaluate answer quality", "validate the answer", "check correctness", "score my answer", "context window is full", "chain multiple research tasks"

---

## Choosing the Right Skill

```
Am I using the USPTO / MPEP corpus?
├── Yes → pinecone-assistant-uspto
│   (extends base skill with domain selection and patent law workflows)
│
└── No (or any corpus)
    ├── On a paid plan or agentic workflow?
    │   └── Yes → pinecone-assistant-paid-plan
    │       (assistant_chat delegation as primary tool)
    │
    └── On free tier or general use
        └── pinecone-assistant
            (context-only tools first, cost-optimized)
```

You can install all three skills — Claude will use the most specific one that matches the context.

---

## Relationship to Prompt Templates

Skills and prompt templates complement each other:

- **Prompt templates** (in the Claude `+` menu) provide structured workflows for common research tasks
- **Skills** provide Claude with deeper guidance on tool selection, parameters, and optimization

| Prompt | Recommended Skill |
|--------|------------------|
| `deep_research` | `pinecone-assistant` or `pinecone-assistant-uspto` |
| `quick_lookup` | `pinecone-assistant` |
| `comparative_research` | `pinecone-assistant` |
| `delegated_research` | `pinecone-assistant-paid-plan` |

See [PROMPTS.md](../PROMPTS.md) for full prompt template documentation.

---

## Updating Skills

Skills are plain Markdown files. To update a skill, edit the `SKILL.md` file and copy it again to `~/.claude/skills/`. Changes take effect in the next Claude Code session.

To verify a skill is loaded in Claude Code:
```
/skills
```

---

*For MCP server setup, see [README.md](../README.md) and [INSTALL.md](../INSTALL.md).*

*For prompt template documentation, see [PROMPTS.md](../PROMPTS.md).*
