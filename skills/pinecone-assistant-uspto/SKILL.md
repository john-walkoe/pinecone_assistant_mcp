---
name: pinecone-assistant-uspto
description: USPTO patent law research using the Pinecone Assistant MCP with MPEP, examination guidelines, and training materials. Provides domain selection for all major patent law issues, USPTO-specific query patterns, and integration workflows with PFW, PTAB, FPD, and Citations MCPs. Use when researching patent law topics or when the pinecone_assistant MCP is connected alongside USPTO MCPs. Triggers on MPEP sections, patent eligibility (§101, Alice, Mayo), obviousness (§103, KSR, Graham), novelty (§102), specification requirements (§112, written description, enablement, indefiniteness), claim construction, PTAB proceedings, IPR petitions, office action responses, prior art analysis, or any patent prosecution or litigation research task. Do NOT trigger for non-patent document corpuses.
metadata:
  author: pinecone-assistant-mcp
  version: 1.0.0
  mcp-server: pinecone_assistant
  category: patent-law-research
  base-skill: pinecone-assistant
---

# Pinecone Assistant MCP - USPTO Patent Law Research Skill

This skill extends the base `pinecone-assistant` skill with USPTO-specific domain knowledge, query patterns, and multi-MCP integration workflows. The pinecone_assistant MCP serves as the **knowledge layer** (MPEP, guidelines, case law) that complements the data-access USPTO MCPs.

## USPTO MCP Ecosystem

| MCP | Role | What It Provides |
|-----|------|-----------------|
| **pinecone_assistant** | Knowledge layer | MPEP guidance, examination standards, case law |
| **PFW MCP** | Data access | Prosecution history, file wrapper documents |
| **PTAB MCP** | Data access | IPR/PGR proceedings, board decisions |
| **FPD MCP** | Data access | First petition data, petition decisions |
| **Citations MCP** | Data access | Prior art citations, examiner citation patterns |

**Always pair pinecone_assistant with the appropriate data MCP** for complete research.

## Domain Selection Guide

Match the patent law issue to the correct domain for `assistant_strategic_multi_search_context` or `assistant_strategic_multi_search_chat`:

| Legal Issue | Domain | When to Use |
|-------------|--------|-------------|
| Alice/Mayo, abstract idea, software eligibility | `section_101_eligibility` | Any §101 rejection or eligibility question |
| KSR, Graham factors, motivation to combine | `section_103_obviousness` | Any §103 rejection or obviousness analysis |
| Written description, enablement, Wands factors | `section_112_requirements` | Any §112 rejection or specification question |
| Anticipation, single reference, inherent disclosure | `section_102_novelty` | Any §102 rejection or novelty analysis |
| Phillips standard, prosecution history estoppel | `claim_construction` | Claim scope disputes, litigation, licensing |
| IPR institution, BRI, PTAB estoppel | `ptab_procedures` | Post-grant proceedings, IPR/PGR analysis |
| Computer-implemented inventions, AI/ML patents | `software_patents` | Tech center 2100/2400 software/AI patents |
| Manufacturing, structural features, TC 3600/3700 | `mechanical_patents` | Mechanical invention examination |
| Broad patent law questions, unknown issue | `general_patent_law` | Starting point when issue is unclear |

## Critical: Temperature for Legal Work

**Always use low temperature** (0.0–0.3) for USPTO research with `assistant_chat`:
- Prevents hallucinated MPEP section numbers or case citations
- Ensures consistent legal interpretations
- Default is already 0.2 — do not raise it for legal analysis

## Core Research Workflows

### Workflow 1: Office Action Response (§101 Eligibility)

```
Step 1 — Research legal framework:
  assistant_strategic_multi_search_context(
    query="[invention description]",
    domain="section_101_eligibility",
    max_searches=3
  )
  → Returns: Alice/Mayo two-step, technological improvement, inventive concept guidance

Step 2 — Pull office action and claims (PFW MCP):
  pfw_get_application_documents(application_number="...", include_raw_xml=False)
  pfw_get_document_by_id(...)

Step 3 — Targeted MPEP lookup for specific argument:
  assistant_context(
    query="MPEP 2106.05(a) technological improvement practical application",
    top_k=4,
    snippet_size=2048
  )

Step 4 — Draft response with practical application arguments
```

### Workflow 2: Office Action Response (§103 Obviousness)

```
Step 1 — Research legal framework:
  assistant_strategic_multi_search_context(
    query="[invention technology area]",
    domain="section_103_obviousness",
    max_searches=4
  )
  → Returns: Graham factors, KSR 7 rationales, secondary considerations

Step 2 — Pull prior art citations (Citations MCP or PFW MCP):
  Analyze what references the examiner cited

Step 3 — Targeted secondary considerations research:
  assistant_context(
    query="secondary considerations commercial success unexpected results long felt need",
    top_k=4
  )

Step 4 — Build Graham factors analysis and secondary considerations arguments
```

### Workflow 3: §112 Specification Issues

```
Step 1 — Identify type of §112 issue:
  - §112(a): Written description / enablement
  - §112(b): Indefiniteness
  - §112(f): Means-plus-function

Step 2 — Research applicable standard:
  assistant_strategic_multi_search_context(
    query="[claim term or technology]",
    domain="section_112_requirements",
    max_searches=3
  )

Step 3 — Targeted lookups by issue type:
  §112(a): assistant_context(query="written description possession requirement MPEP 2163")
  §112(b): assistant_context(query="Nautilus reasonable certainty indefiniteness MPEP 2173")
  §112(f): assistant_context(query="means-plus-function corresponding structure MPEP 2181")

Step 4 — Pull specification via PFW MCP for comparison
```

### Workflow 4: PTAB / IPR Analysis

```
Step 1 — Research institution standards:
  assistant_strategic_multi_search_context(
    query="IPR institution petition standards",
    domain="ptab_procedures",
    max_searches=3
  )

Step 2 — Find existing PTAB proceedings (PTAB MCP):
  search_trials_minimal(patent_number="...", limit=10)

Step 3 — Research relevant legal issues in the proceeding:
  assistant_context(
    query="[primary rejection type in IPR] PTAB institution decision",
    top_k=5
  )

Step 4 — Analyze claim construction approach:
  assistant_strategic_multi_search_context(
    query="[claim terms in dispute]",
    domain="claim_construction"
  )
```

### Workflow 5: Patent Invalidity Defense (Full Multi-MCP)

```
Step 1 — Detect primary vulnerability from prosecution history
Step 2 — Research legal framework via pinecone_assistant:
  assistant_strategic_multi_search_context(domain="[detected domain]")
Step 3 — Pull prosecution history (PFW MCP)
Step 4 — Check PTAB history (PTAB MCP)
Step 5 — Analyze citations (Citations MCP)
Step 6 — Deep-dive research on secondary issues:
  assistant_context(query="[specific legal issue]", top_k=5)
Step 7 — Synthesize defense strategy
```

## Query Patterns for USPTO Research

**Include statutory section numbers and MPEP references:**
```
GOOD: "Section 101 Alice Mayo two-step framework abstract idea software"
GOOD: "MPEP 2106.04 judicial exceptions categories analysis"
GOOD: "KSR motivation to combine predictable results rationale"
GOOD: "Nautilus reasonable certainty indefiniteness §112(b) POSITA"
```

**Include technology specifics when relevant:**
```
GOOD: "AI machine learning patent eligibility practical application §101"
GOOD: "pharmaceutical formulation obviousness teaching away secondary considerations"
GOOD: "computer-implemented method abstract idea technological improvement"
```

**Include case names for targeted case law research:**
```
GOOD: "Alice Corp CLS Bank abstract idea step two significantly more"
GOOD: "KSR Teleflex motivation combine seven rationales"
GOOD: "Graham John Deere four factors secondary considerations"
GOOD: "Phillips AWH intrinsic extrinsic evidence claim construction"
GOOD: "Nautilus Biosig reasonable certainty definiteness"
```

## Domain-Specific Query Examples

### §101 Eligibility
```
"Section 101 Alice Mayo two-step abstract idea [technology]"
"MPEP 2106 judicial exceptions practical application"
"software patent eligibility technological improvement computer functionality"
"AI machine learning patent §101 significantly more inventive concept"
```

### §103 Obviousness
```
"KSR motivation to combine [technology] predictable results"
"Graham factors scope prior art level ordinary skill POSITA [field]"
"secondary considerations commercial success unexpected results [invention type]"
"teaching away prior art [technology] motivation combine"
```

### §112 Requirements
```
"written description possession requirement MPEP 2163 [technology]"
"enablement Wands factors undue experimentation [technology]"
"indefiniteness Nautilus reasonable certainty [claim term]"
"means-plus-function §112(f) corresponding structure specification"
```

### Claim Construction
```
"Phillips claim construction intrinsic evidence specification [term]"
"prosecution history estoppel argument-based surrender [amendment type]"
"functional claiming 112(f) module mechanism structure disclosure"
```

## USPTO Multi-Assistant Setup

Maximize coverage across the MPEP with multiple specialized assistants:

```
mpep-core-assistant       → MPEP 9th Edition core chapters (Parts 1-4)
mpep-updates-assistant    → Federal Register notices and recent guidances
mpep-training-assistant   → USPTO training materials and examination examples
case-law-assistant        → Federal Circuit and PTAB decisions
examination-assistant     → Art-unit specific examination guidelines
```

**Research flow across assistants:**
```
1. Start with mpep-core-assistant for foundational MPEP guidance
2. update_configuration(assistant_name="mpep-updates-assistant")
   → Check for recent guidance updates on the same topic
3. update_configuration(assistant_name="case-law-assistant")
   → Research supporting case law and PTAB precedent
4. Synthesize findings from all three sources
```

## Integration with Other USPTO MCPs

### pinecone_assistant + PFW MCP (Most Common Combination)
```
pinecone_assistant → What does the law/MPEP say about this issue?
PFW MCP           → What does the actual prosecution file show?
Combined           → Draft office action response or prosecution strategy
```

### pinecone_assistant + PTAB MCP
```
pinecone_assistant → What are the legal standards for IPR institution?
PTAB MCP           → What have actual PTAB boards decided on similar patents?
Combined           → Assess institution likelihood and build petition/response
```

### pinecone_assistant + Citations MCP
```
Citations MCP      → What prior art did the examiner cite? (post Oct 2017)
pinecone_assistant → What does MPEP say about anticipation/obviousness with these references?
Combined           → Build targeted prior art arguments
```

### pinecone_assistant + FPD MCP
```
FPD MCP            → What petitions were filed? What did the Director decide?
pinecone_assistant → What is the legal basis for the petition type?
Combined           → Analyze petition strategy and precedent
```

## Token Budget for USPTO Research

USPTO research sessions often involve multiple MCPs. Manage tokens carefully:

| Step | Tool | ~Token Cost |
|------|------|-------------|
| MPEP framework research | `assistant_strategic_multi_search_context` | 10-20K context |
| Targeted MPEP lookup | `assistant_context` | 5-10K context |
| Deep-dive case law | `assistant_context` (top_k=5) | 8-12K context |
| Prosecution history (PFW) | `pfw_get_application_documents(include_raw_xml=False)` | 3-5K |
| Office action retrieval | `pfw_get_document_by_id` | 10-30K |
| PTAB trial search | `search_trials_minimal` | 2-5K |

**Reserve 20% of context for final synthesis and output.**

**Use `include_raw_xml=False`** in all PFW calls unless specific XML content is needed — saves 45-75K tokens per call.

## Common Research Scenarios

### Scenario: Software Patent §101 Rejection
```
domain: "section_101_eligibility" OR "software_patents"
queries: [
  "Alice step 2A Prong 2 practical application [technology]",
  "technological improvement computer functionality §101",
  "MPEP 2106.05(a) improvement technology"
]
PFW: Pull office action, claims, specification
```

### Scenario: §103 Obviousness Rejection
```
domain: "section_103_obviousness"
queries: [
  "KSR motivation to combine [tech area]",
  "secondary considerations commercial success unexpected results",
  "teaching away prior art [specific feature]"
]
Citations MCP: Identify examiner's cited references
PFW: Pull office action
```

### Scenario: Pre-Filing Prior Art Search
```
domain: "section_102_novelty" then "section_103_obviousness"
queries: [
  "anticipation single reference [technology]",
  "obviousness combination [technology]",
  "[key claim features] prior art disclosure"
]
No PFW needed — pure knowledge base research
```

### Scenario: IPR Petition Preparation
```
domain: "ptab_procedures" then "section_103_obviousness" or "section_102_novelty"
queries: [
  "IPR institution decision reasonable likelihood standard",
  "BRI broadest reasonable interpretation PTAB",
  "[grounds for challenge] MPEP guidance"
]
PTAB MCP: Search similar institution decisions
PFW MCP: Pull prosecution history for estoppel analysis
```

### Scenario: Claim Construction Analysis
```
domain: "claim_construction"
queries: [
  "Phillips intrinsic evidence specification [claim term]",
  "prosecution history estoppel [amendment type]",
  "functional claiming means-plus-function [claim language]"
]
PFW MCP: Pull prosecution history
```
