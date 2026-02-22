# Pinecone Assistant MCP - Usage Examples

This document provides comprehensive examples and guidance for using the Pinecone Assistant MCP effectively, with token optimization strategies and best practices.

**Note**: This guide uses USPTO patent examination as the reference implementation, but the patterns apply to any document corpus.

### Multi-turn Conversation Token Management

**CRITICAL**: The Pinecone Assistant API is **stateless** - it has no memory between requests.

#### When to Include Conversation History ✅

**Only include history when the new question explicitly references prior context:**

- **Pronouns**: "that", "this", "it", "those", "these"
- **References**: "as mentioned", "the above", "previously discussed"
- **Continuation**: "follow up", "expand on", "additionally"

**Example requiring history**:
```json
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [
      {"role": "user", "content": "What is the Alice/Mayo framework?"},
      {"role": "assistant", "content": "[Previous AI response]"},
      {"role": "user", "content": "How does THAT framework apply to ML patents?"}
    ]
  }
}
```

#### When NOT to Include History ❌

**Do NOT include history when questions are independent:**

**Bad (wasteful)**:
```json
{
  "messages": [
    {"role": "user", "content": "What is Section 101?"},
    {"role": "assistant", "content": "[1000 token response]"},
    {"role": "user", "content": "What is Section 103?"}  // Independent question!
  ]
}
```

**Good (efficient)**:
```json
{
  "messages": [
    {"role": "user", "content": "What is Section 103?"}  // Stateless
  ]
}
```

#### Token Impact Example

**4-turn conversation comparison:**

- **Wasteful (full history)**: 130K input tokens total
- **Smart (stateless when possible)**: 124K input tokens total
- **Savings**: 6K tokens = 3-5 additional chat queries from your lifetime allocation

**Default pattern**: Send single-message queries. Only add history if the new question literally cannot be understood without prior context.

### Temperature Configuration

**Default: 0.2 (Low Temperature for Legal/USPTO Precision)**

The MCP is configured with a low default temperature (0.2) optimized for patent law and legal analysis:

**Why Low Temperature for USPTO/Legal Work:**
- **Accurate Citations**: Prevents AI from inventing MPEP sections or case names
- **Consistent Analysis**: Same query yields consistent legal interpretations
- **Factual Precision**: Critical for exact statute/regulation references
- **Risk Mitigation**: Reduces hallucinations in legal advice
- **IRAC Reliability**: Structured analysis requires deterministic responses

**Temperature Guide:**

| Temperature | Behavior | Best For | USPTO Suitability |
|-------------|----------|----------|-------------------|
| **0.0 - 0.3** | Deterministic, precise | Legal citations, factual analysis | ✅ **Recommended** |
| **0.4 - 0.7** | Balanced | General research | ⚠️ Acceptable for exploratory research |
| **0.8 - 2.0** | Creative, varied | Brainstorming, creative writing | ❌ Not recommended for legal work |

**Override Temperature:**
```json
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [...],
    "temperature": 0.3  // Override default for this specific query
  }
}
```

**Custom Domains:**
Set higher temperature for creative domains via environment variable:
```bash
export DEFAULT_TEMPERATURE=0.7  # For creative/brainstorming domains
```

### Free Tier Budget Management

**Lifetime Token Allocation:**

- Input tokens: 1.5M
- Context tokens: 500K
- Output tokens: 200K

**Usage estimates (total lifetime, not per month — these do NOT reset):**

- `assistant_context`: ~50+ total queries (context tokens)
- `assistant_strategic_multi_search_context`: ~20-30 total queries (context tokens)
- `assistant_strategic_multi_search_chat`: ~50-75 total queries (input tokens)
- `assistant_chat` (with smart history): ~50 total queries (input tokens)
- `assistant_chat` (with wasteful history): ~35 total queries (input tokens)

## 🎯 Domain Organization & Use Cases

### Domain Selection Guide

| Domain | Focus Area | Typical Use Cases | Search Patterns |
|--------|-----------|-------------------|-----------------|
| **`section_101_eligibility`** | Patent eligibility analysis | Alice/Mayo rejections, abstract idea analysis | 4 searches |
| **`section_103_obviousness`** | Obviousness analysis | KSR factors, prior art combination | 4 searches |
| **`section_112_requirements`** | Specification compliance | Written description, enablement, definiteness | 4 searches |
| **`section_102_novelty`** | Prior art and anticipation | Novelty rejections, prior art dates | 3 searches |
| **`claim_construction`** | Claim interpretation | Phillips standard, prosecution history | 3 searches |
| **`ptab_procedures`** | Post-grant proceedings | IPR/PGR, PTAB claim construction | 3 searches |
| **`mechanical_patents`** | Mechanical inventions | Mechanical obviousness, manufacturing | 2 searches |
| **`software_patents`** | Software/AI inventions | Software eligibility, AI/ML patents | 2 searches |
| **`general_patent_law`** | General guidance | Broad patent law questions | 5 searches |

### 🔧 Domain Design Rationale

Domains are organized by **legal issue** rather than workflow stage, enabling:
- **Direct issue targeting**: Select domain matching your specific legal question
- **Cross-reference capability**: Combine multiple domains for complex analysis
- **Technology-specific searches**: `software_patents` and `mechanical_patents` for tech-focused guidance

**Selection Strategy:**
- **Specific rejection type** → Use matching section domain (101, 102, 103, 112)
- **Technology-specific** → Use `software_patents` or `mechanical_patents`
- **General research** → Start with `general_patent_law`
- **Post-grant** → Use `ptab_procedures` or `claim_construction`

## 📚 Detailed Usage Scenarios

### Scenario 1: Section 101 Rejection (Software Patent)

**Situation**: Received Alice/Mayo rejection on machine learning algorithm patent

```json
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "machine learning algorithm patent eligibility",
    "domain": "section_101_eligibility",
    "max_searches": 3
  }
}
```

**Searches Executed**:
- Alice/Mayo framework analysis
- Technological improvement vs abstract idea
- Inventive concept analysis

**Workflow**:
1. **Strategic search** → Get Alice/Mayo framework and practical application guidance
2. **PFW MCP** → Pull office action with 101 rejection
3. **Draft response** using MPEP examples and case law

**Expected Results**:
- Alice/Mayo two-step framework application
- Technological improvement arguments
- Inventive concept analysis for Step 2

---

### Scenario 2: Office Action Response (103 Rejection)

**Situation**: Need to overcome obviousness rejection for pharmaceutical formulation

```json
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "pharmaceutical formulation prior art combination",
    "domain": "section_103_obviousness",
    "max_searches": 4
  }
}
```

**Searches Executed**:
- Graham factors analysis
- KSR motivation to combine rationales
- Secondary considerations of non-obviousness
- Prior art combination analysis

**Workflow**:
1. **PFW MCP** → Get office action and prior art references
2. **Strategic search** → Find KSR rationales and secondary considerations guidance
3. **Draft response** with Graham factors and secondary considerations arguments

**Expected Results**:
- Graham v. John Deere four-factor framework
- KSR motivation to combine analysis
- Secondary considerations arguments (commercial success, teaching away)

---

### Scenario 3: IPR Institution Decision Analysis

**Situation**: Analyzing likelihood of IPR institution for challenged patent

```json
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "IPR institution standards claim construction",
    "domain": "ptab_procedures",
    "max_searches": 3
  }
}
```

**Searches Executed**:
- IPR petition and institution standards
- PTAB claim construction standards
- PTAB estoppel rules

**Workflow**:
1. **Strategic search** → Get institution standards and claim construction guidance
2. **PTAB MCP** → Search similar IPR proceedings and institution decisions
3. **Analyze** likelihood of institution based on precedent

**Expected Results**:
- IPR institution standards and preponderance of evidence requirements
- PTAB claim construction methodology (BRI/Phillips)
- Estoppel implications for non-instituted grounds

---

### Scenario 4: Written Description Rejection

**Situation**: Responding to Section 112(a) written description rejection

```json
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "written description possession requirement biotechnology",
    "domain": "section_112_requirements",
    "max_searches": 2
  }
}
```

**Searches Executed**:
- Written description requirement analysis
- Enablement requirement and Wands factors

**Workflow**:
1. **Strategic search** → Get written description and enablement standards
2. **PFW MCP** → Pull specification and office action
3. **Draft response** with possession and enablement arguments

**Expected Results**:
- Written description possession requirement (§112(a))
- Enablement standards and Wands factors
- Specification support analysis

---

### Scenario 5: Claim Construction Dispute

**Situation**: Analyzing claim scope for litigation or licensing

```json
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "claim construction means-plus-function limitations",
    "domain": "claim_construction",
    "max_searches": 3
  }
}
```

**Searches Executed**:
- Phillips v. AWH claim construction standard
- Prosecution history estoppel analysis
- Functional claim language interpretation

**Workflow**:
1. **Strategic search** → Get claim construction standards and Phillips analysis
2. **PFW MCP** → Review prosecution history for estoppel issues
3. **Analyze** claim scope using intrinsic and extrinsic evidence

**Expected Results**:
- Phillips standard for claim construction
- Prosecution history estoppel principles
- Means-plus-function interpretation under §112(f)

## 📝 MCP Prompts

Four corpus-neutral prompt templates are accessible from the Claude prompt menu. Each generates a pre-filled workflow with structured tool calls — select from the prompt menu and fill in the arguments.

| Prompt | Parameters | Token Tier | Use When |
|--------|-----------|-----------|---------|
| `deep_research` | `topic`, `domain?` | Context only | Thorough multi-angle coverage |
| `quick_lookup` | `topic` | Context only | Fast single-fact retrieval |
| `comparative_research` | `topic_a`, `topic_b` | Context only | Side-by-side topic comparison |
| `delegated_research` | `research_question`, `model?`, `prior_context?` | Context + LLM | Paid plan / agentic synthesis |

### `deep_research`

Executes `assistant_strategic_multi_search_context` with `max_searches=4`, then fills gaps with targeted `assistant_context` calls. Context tokens only — no AI synthesis cost.

**Example**: `topic="Alice/Mayo two-step framework software patents"`, `domain="section_101_eligibility"`

### `quick_lookup`

Single `assistant_context` call with `top_k=3, snippet_size=1024`. Under 5K context tokens. One retry with broader terminology if initial results are irrelevant.

**Example**: `topic="MPEP 2106.05(a) practical application"`

### `comparative_research`

Two sequential `assistant_context` calls — one per topic — then structured comparison output covering similarities, differences, and when to apply each.

**Example**: `topic_a="written description requirement"`, `topic_b="enablement requirement"`

### `delegated_research`

Delegates synthesis to the Pinecone Assistant AI via `assistant_chat`. Pinecone handles internal retrieval and synthesis; Claude receives only the compact result. Supports stateless single queries and follow-up queries with prior context.

**Example**: `research_question="What are the key differences between IPR and PGR institution standards?"`, `model="gpt-4o"`

**Follow-up with prior context**: Paste the prior assistant answer into `prior_context` when the new question references it. Omit `prior_context` for independent questions (stateless = cheapest).

---

## 🔀 Delegation Workflow (Paid Plan / Agentic)

`assistant_chat` functions as a sub-agent delegation mechanism — Pinecone internally retrieves context from the knowledge base, feeds it to the configured LLM, and returns a synthesized, citation-backed answer. Claude receives only the compact result (~500–2000 tokens) rather than raw document chunks, preserving Claude's context window for orchestration.

### Single Delegated Query

```json
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [{"role": "user", "content": "What are the seven KSR rationales for combining prior art references?"}],
    "model": "gpt-4o",
    "temperature": 0.2,
    "include_highlights": true,
    "context_options": {"top_k": 5, "snippet_size": 2048}
  }
}
```

### Agentic Chaining (Multiple Independent Questions)

Chain independent calls without history — each is stateless, no accumulated cost:

```json
// Call 1: First research topic
{"tool": "assistant_chat", "arguments": {"messages": [{"role": "user", "content": "IPR institution standards"}]}}

// Call 2: Second independent topic — no history
{"tool": "assistant_chat", "arguments": {"messages": [{"role": "user", "content": "PGR institution standards"}]}}

// Synthesize both results in Claude's context
```

### Follow-Up With Prior Context

Include history **only** when the new question explicitly references the prior answer:

```json
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [
      {"role": "user", "content": "What are the Graham v. John Deere four factors?"},
      {"role": "assistant", "content": "[prior answer text]"},
      {"role": "user", "content": "How do those factors apply to pharmaceutical formulations?"}
    ],
    "context_options": {"top_k": 5, "snippet_size": 2048}
  }
}
```

### context_options Tuning

Control how much context Pinecone sends to its LLM per call:

| Setting | Tokens to LLM | Use When |
|---------|--------------|---------|
| `{"top_k": 3, "snippet_size": 1024}` | ~3K | Focused single-concept question |
| `{"top_k": 5, "snippet_size": 2048}` | ~10K | Standard research (recommended) |
| `{"top_k": 10, "snippet_size": 2048}` | ~20K | Broad topic needing wide coverage |

### Mixing Delegation with Context Retrieval

Use `assistant_chat` for broad synthesis, then `assistant_context` for targeted follow-up gaps:

```json
// Step 1: Broad synthesis via delegation
{"tool": "assistant_chat", "arguments": {"messages": [{"role": "user", "content": "Overview of §101 eligibility framework"}], "context_options": {"top_k": 5, "snippet_size": 2048}}}

// Step 2: Targeted gap fill via context retrieval (cheaper)
{"tool": "assistant_context", "arguments": {"query": "MPEP 2106.05(a) practical application technological improvement", "top_k": 3}}
```

### `assistant_context` New Parameters

**Multimodal and messages support** expand what `assistant_context` can retrieve:

```json
// With multimodal disabled (text-only retrieval, smaller response)
{
  "tool": "assistant_context",
  "arguments": {
    "query": "Section 101 eligibility",
    "top_k": 5,
    "multimodal": false,
    "include_binary_content": false
  }
}
```

```json
// With messages input (multi-turn context retrieval)
{
  "tool": "assistant_context",
  "arguments": {
    "messages": [
      {"role": "user", "content": "What is the Alice/Mayo framework?"},
      {"role": "assistant", "content": "[prior response]"},
      {"role": "user", "content": "How does that apply to software patents?"}
    ],
    "top_k": 5
  }
}
```

**Parameter notes:**
- `query` is now optional — either `query` OR `messages` is required
- `multimodal` (optional bool): Enable image retrieval from PDFs. Only works with `query` input
- `include_binary_content` (optional bool): Include base64 image data in response. Set `false` to reduce response size. Only works with `query` input
- When using `messages`, the `multimodal` and `include_binary_content` parameters are ignored by the API

### `assistant_chat` Response Format

`assistant_chat` returns **clean text**, not JSON. The response contains:
1. The answer content
2. A **Sources** section listing filename and a ~150-character excerpt per source
3. A token summary line

**Example response format:**
```
[Answer text here...]

**Sources:**
- MPEP_Part2.md: "...the Alice/Mayo framework requires a two-step analysis. Step 2A asks whether..."
- Combined_Training_Materials.md: "...software claims directed to abstract ideas must provide significantly more..."

*Tokens: 35,205 prompt + 823 completion = 36,028 total*
```

---

## 🚀 Advanced Usage Patterns

### Multi-Tool Workflow Integration

For complex patent prosecution tasks, combine the Pinecone Assistant with other USPTO MCPs:

#### Section 101 Rejection Response
```bash
# 1. Get Alice/Mayo framework guidance
assistant_strategic_multi_search_chat → domain: "section_101_eligibility"

# 2. Pull office action
PFW MCP → Download office action and specifications

# 3. Draft response with practical application arguments
```

#### Section 103 Obviousness Analysis
```bash
# 1. Research KSR and Graham factors
assistant_strategic_multi_search_chat → domain: "section_103_obviousness"

# 2. Analyze prior art
PFW MCP → Get prior art references and examiner analysis

# 3. Build secondary considerations case
```

#### PTAB Proceeding Preparation
```bash
# 1. Research institution standards
assistant_strategic_multi_search_chat → domain: "ptab_procedures"

# 2. Find similar proceedings
PTAB MCP → Search institution decisions

# 3. Analyze claim construction approach
```

### Conversation Continuation Strategies

Use `assistant_chat` for follow-up questions after strategic searches:

```json
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [
      {
        "role": "user",
        "content": "Based on the strategic search results, what specific KSR factors should I emphasize for a pharmaceutical formulation obviousness argument?"
      }
    ],
    "model": "gpt-4o",
    "include_highlights": true
  }
}
```

## 💡 Best Practices

### When to Use Strategic Search vs Direct Chat

**Use `assistant_strategic_multi_search_chat` when**:
- Starting research on a broad topic
- Need comprehensive coverage of related issues
- Want systematic analysis across multiple guidance documents
- Preparing for complex prosecution or post-grant procedures

**Use `assistant_chat` when**:
- Following up on specific findings
- Need clarification on particular guidance
- Have targeted questions about specific procedures
- Want to explore nuances of a particular topic

### Domain Selection Tips

1. **Match rejection type**: Section 101 → `section_101_eligibility`, 103 → `section_103_obviousness`, etc.
2. **Consider technology**: Software/AI → `software_patents`, Mechanical → `mechanical_patents`
3. **Legal issue focus**: Use specific section domains (101, 102, 103, 112) for targeted analysis
4. **General research**: Start with `general_patent_law` for broad questions
5. **Post-grant matters**: Use `ptab_procedures` or `claim_construction`

### Context Management

- **Strategic searches**: Use for initial comprehensive research (20-30K tokens)
- **Follow-up chats**: Use for specific questions (5-15K tokens)
- **Document specific**: Switch to PFW/PTAB/FPD MCPs for specific documents
- **Monitor usage**: Claude Desktop shows token consumption per interaction

## 🔍 Troubleshooting

### Common Issues and Solutions

**"Strategic search returns too broad results"**
- Use more specific query terms
- Reduce `max_searches` parameter to 2
- Switch to `assistant_chat` for targeted questions

**"Need more specific technology guidance"**
- Use appropriate technology domain: `software_patents` or `mechanical_patents`
- Follow up with specific section domains (101, 102, 103) for rejection-specific analysis
- Cross-reference with PFW MCP for technology center guidance

**"Context limit reached"**
- Switch to direct `assistant_chat` for remaining questions
- Use PFW/PTAB/FPD MCPs for document-specific research
- Save strategic search results and start new conversation

---

## 🔀 Multi-Assistant Workflows

**Leverage up to 5 Pinecone Assistants (free tier)** for specialized knowledge bases using the `update_configuration` tool.

### Example: USPTO Research Setup

**Create specialized assistants:**
```
1. mpep-assistant          → MPEP 9th Edition core guidance (Combined_MPEP_9th_Edition_Part1-4.md)
2. updates-assistant       → Recent Federal Register notices & updates (Combined_MPEP_Updates.md)
3. case-law-assistant      → Federal Circuit & PTAB decisions (Not included)
4. training-assistant      → USPTO training materials & examples (Combined_Training_Materials.md)
5. international-assistant → PCT, Paris Convention, treaties (Not included)
```

**Mid-Conversation Switching:**

```
User: "What does MPEP § 2138.04 say about AI inventorship?"
[Using mpep-assistant - returns MPEP guidance]

User: use update_configuration(assistant_name: "updates-assistant")
✅ Switched to updates-assistant

User: "What recent Federal Register guidance addresses AI inventorship?"
[Now using updates-assistant - returns 2024 guidance]

User: use update_configuration(assistant_name: "case-law-assistant")
✅ Switched to case-law-assistant

User: "How have courts applied these principles in recent cases?"
[Now using case-law-assistant - returns Thaler v. Vidal analysis]
```

**Benefits:**
- Single conversation spans multiple knowledge bases
- 10 file limit per assistant (free tier) → 50 files total across 5 assistants
- Specialized metadata and search patterns per assistant
- Maintain conversation context while switching sources

### Other Domain Examples

**Medical Research:**
- `clinical-trials` → Clinical trial databases
- `literature` → PubMed and research papers
- `guidelines` → Medical society practice guidelines
- `pharmacology` → Drug interactions and dosing
- `imaging` → Radiology and diagnostic criteria

**Financial Analysis:**
- `sec-filings` → 10-K, 10-Q, 8-K reports
- `earnings` → Earnings call transcripts
- `analyst` → Analyst reports and ratings
- `economic` → Economic indicators and Fed minutes
- `regulations` → GAAP, IFRS, regulatory guidance

**Software Development:**
- `documentation` → API docs, technical specifications
- `architecture` → System design patterns, best practices
- `security` → Security guidelines, vulnerability reports
- `performance` → Optimization guides, benchmarking data
- `frameworks` → Framework-specific guides and examples

### Multi-Assistant Best Practices

**Setup Strategy:**
1. **Domain Separation**: Keep related but distinct content in separate assistants
2. **Size Management**: Stay within 10 file limit per assistant by splitting logically
3. **Naming Convention**: Use descriptive names that indicate content type
4. **Search Patterns**: Customize `strategic-searches.yaml` per assistant's content

**Workflow Optimization:**
1. **Start Broad**: Begin with general knowledge base (e.g., `mpep-assistant`)
2. **Narrow Down**: Switch to specialized assistants for specific analysis
3. **Cross-Reference**: Use multiple assistants to verify information
4. **Context Preservation**: Claude Desktop maintains conversation context across switches

**Token Management:**
- Use context tools first in each assistant to minimize costs
- Switch assistants when you need different knowledge, not for token limits
- Each assistant switch resets internal state but preserves Claude conversation

**Example Multi-Assistant Research Flow:**

```json
// Step 1: General guidance
{
  "tool": "assistant_context",
  "arguments": {
    "query": "Section 101 software patent eligibility requirements"
  }
}

// Step 2: Switch to recent updates
{
  "tool": "update_configuration", 
  "arguments": {
    "assistant_name": "updates-assistant"
  }
}

// Step 3: Check recent guidance
{
  "tool": "assistant_context",
  "arguments": {
    "query": "AI patent eligibility guidance 2024 2025"
  }
}

// Step 4: Switch to case law
{
  "tool": "update_configuration",
  "arguments": {
    "assistant_name": "case-law-assistant" 
  }
}

// Step 5: Analyze precedent
{
  "tool": "assistant_strategic_multi_search_chat",
  "arguments": {
    "query": "software patent eligibility Federal Circuit decisions",
    "domain": "section_101_eligibility"
  }
}
```

This approach gives you comprehensive coverage while staying within free tier limits and optimizing token usage across multiple specialized knowledge bases.

---

## 📊 Answer Evaluation

### `evaluate_answer` *(Paid Plan Only)*
**Evaluate AI answer quality against a ground truth.**

> **Requires Pinecone Standard (paid) plan.** Free tier users will receive an error. Rate limited to 20 requests/minute.

**Use case:** After getting an answer from `assistant_chat`, evaluate its accuracy against a known-correct answer.

```json
{
  "tool": "evaluate_answer",
  "arguments": {
    "question": "What is the Alice/Mayo two-step test?",
    "answer": "The Alice/Mayo framework has two steps. Step 2A asks whether the claim is directed to a judicial exception (abstract idea, law of nature, or natural phenomenon). Step 2B determines whether additional elements amount to significantly more than the judicial exception.",
    "ground_truth_answer": "The Alice/Mayo test is a two-step framework established by Alice Corp. v. CLS Bank (2014) and Mayo Collaborative Services v. Prometheus (2012). Step 1 asks whether the claim is directed to a judicial exception. Step 2 asks whether the claim includes additional elements that amount to significantly more than the exception alone, providing an inventive concept."
  }
}
```

**Response format:**
```
**Alignment Scores:**
- Alignment (overall): 0.847
- Correctness (precision): 0.900
- Completeness (recall): 0.800

**Evaluated Facts:**
  [entailed] Two-step framework
  [entailed] Step 2A asks whether claim is directed to judicial exception
  [entailed] Judicial exceptions include abstract ideas, laws of nature, natural phenomena
  [neutral] Established by Alice Corp. v. CLS Bank (2014)
  [contradicted] Step 2 is called Step 2B (answer uses "Step 2B" for what ground truth calls "Step 2")

*Tokens: 1,204 prompt + 87 completion = 1,291 total*
```

**Score interpretation:**
- **alignment >= 0.8**: High quality answer
- **alignment 0.5–0.8**: Acceptable but incomplete
- **alignment < 0.5**: Significant gaps or errors

**Workflow example — evaluate after delegation:**

```json
// Step 1: Get answer via delegation
{
  "tool": "assistant_chat",
  "arguments": {
    "messages": [{"role": "user", "content": "What is the Alice/Mayo two-step test?"}],
    "model": "gpt-4o"
  }
}

// Step 2: Evaluate the answer against a known-correct reference
{
  "tool": "evaluate_answer",
  "arguments": {
    "question": "What is the Alice/Mayo two-step test?",
    "answer": "[paste the answer from Step 1]",
    "ground_truth_answer": "[your verified reference answer]"
  }
}
```

---

*This document is maintained alongside the Pinecone Assistant MCP. For the latest version and updates, see the [main repository](https://github.com/john-walkoe/pinecone_assistant_mcp).*