<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Frontier Methodology: Building a Rational Engineering Memory System

Research date: 2026-06-23

## Purpose

This document describes the methodology behind DREAM: how to build an AI
engineering memory system that is useful, source-grounded, incrementally
maintained, and safe enough for real engineering workflows.

The central claim is:

> A production-grade engineering memory system should not store LLM summaries as
> facts. It should extract evidence-backed candidate claims from repositories,
> documentation, runbooks, incidents, and PR history, then promote only
> validated claims into durable memory.

## Methodology Summary

DREAM should be built as a governed memory pipeline:

```text
Source artifacts
  -> deterministic structure extraction
  -> semantic claim extraction
  -> evidence graph construction
  -> generated human/agent artifacts
  -> validation and eval
  -> human review gates
  -> durable memory promotion
  -> incremental refresh
```

This methodology is supported by recent work in repository knowledge graphs,
automated repository documentation, temporal knowledge graphs, GraphRAG,
schema-guided knowledge extraction, and evaluation science.

## Principle 1: Start with Deterministic Repository Structure

LLMs are useful for semantic interpretation, but source-code structure should be
extracted deterministically where possible.

Use parsers, ASTs, Tree-sitter, LSP, or language-specific analyzers to build a
`RepoGraph` containing:

- packages and modules
- classes, functions, methods
- imports and dependencies
- API endpoints, jobs, tasks, handlers, and adapters
- tests and test mappings
- build, deployment, and workflow metadata
- file ownership or path ownership if available

### Paper Support

[RepoDoc](https://arxiv.org/html/2604.26523v1) argues that automated
documentation systems should use a repository knowledge graph as the semantic
backbone. Its RepoKG construction supports modular documentation, semantic
impact propagation, and selective regeneration after code changes.

The reported evaluation covers 24 repositories across 8 languages and shows
substantial improvements in API coverage, completeness, generation speed, token
usage, and incremental update performance.

### DREAM Implication

DREAM should make `RepoGraph` the stable substrate. The LLM should not be asked
to infer basic structural facts such as "what imports what" or "which test maps
to which class" when these can be extracted from code.

## Principle 2: Use Hierarchical Decomposition for Large Codebases

Large repositories cannot be treated as flat text. The system must decompose the
codebase into coherent modules, generate local understanding, and synthesize
larger system views from smaller verified artifacts.

### Paper Support

[CodeWiki](https://arxiv.org/abs/2510.24428) and its open-source implementation
[FSoft-AI4Code/CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki) provide a
strong reference for repository-level documentation generation. CodeWiki uses
hierarchical decomposition, recursive agentic processing, and multi-modal
synthesis to generate architecture-aware documentation and diagrams.

### DREAM Implication

DREAM should not index every artifact into one global prompt. It should create:

- leaf-level memories for source-backed local facts
- module-level memories for coherent subsystem behavior
- system-level memories for cross-module workflows and risks

This layered approach makes review and evaluation possible.

## Principle 3: Separate Structural Graphs from Semantic Memory

DREAM needs two related but distinct graphs:

1. `RepoGraph`: deterministic code and artifact structure.
2. `MemoryGraph`: semantic claims about behavior, decisions, risks, runbooks,
   incidents, ownership, and operating knowledge.

The `RepoGraph` answers structural questions. The `MemoryGraph` answers
engineering meaning questions. They should be linked but not collapsed into one
untyped graph.

## Principle 4: Represent Memory as Atomic Claims

Durable memory should be an atomic, typed claim:

```text
entity
relation
value
condition
confidence
source_ids
evidence_span
valid_from
valid_until
review_status
```

Avoid storing large narrative summaries as authoritative memory. Summaries are
generated artifacts. Atomic claims are memory candidates.

### Why This Matters

Atomic claims can be validated, reviewed, superseded, and diffed. Narrative
summaries cannot be reliably evaluated or maintained when the underlying code
changes.

## Principle 5: Track Time and Fact Validity

Engineering systems evolve. A true fact from last quarter can become false after
a refactor, incident, migration, or runbook update.

### Paper and Project Support

[Graphiti](https://github.com/getzep/graphiti) and the Zep paper
[A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/html/2501.13956v1)
argue for temporal context graphs where facts have provenance and validity
windows. Graphiti tracks how facts change over time and supports incremental
updates without full graph recomputation.

### DREAM Implication

DREAM memory should support:

- `valid_from`
- `valid_until`
- superseded-by links
- stale candidates
- source freshness
- conflicting facts
- historical facts that remain useful but are no longer current

This is critical for PR review, incident learning, runbook safety, and
architecture evolution.

## Principle 6: Build GraphRAG for Reasoning, Not Just Retrieval

Vector retrieval is insufficient for engineering memory because many questions
are relational:

- Which services are affected by this requirement?
- Which tests cover this behavior?
- Which incident taught us this runbook rule?
- Which PR changed the older architectural assumption?
- Which owner needs to review this memory update?

### Paper Support

[GraphRAG-Bench](https://arxiv.org/html/2506.02404v2) evaluates graph retrieval
augmented generation across graph construction, retrieval, answer generation,
and rationale quality. It supports the idea that graph quality and reasoning
paths should be evaluated separately from final answer text.

[Microsoft GraphRAG](https://microsoft.github.io/graphrag/) demonstrates
entity, relationship, claim, and community-summary extraction from raw text for
global sensemaking.

### DREAM Implication

DREAM should store evidence paths, not just retrieved chunks:

```text
requirement -> concept -> code file -> test -> incident -> historical PR -> review rule
```

The path itself is part of the answer and part of the audit trail.

## Principle 7: Use Schema-Guided Extraction with Controlled Evolution

Free-form triples become a junk drawer quickly. DREAM should use an explicit,
versioned schema for memory extraction.

Initial node types:

- service
- module
- code_file
- test
- endpoint
- job
- runbook
- incident
- decision
- risk
- owner
- requirement
- PR

Initial edge types:

- implements
- calls
- depends_on
- tested_by
- documented_by
- caused_by
- mitigated_by
- supersedes
- conflicts_with
- owned_by
- reviewed_by
- evidence_for

### Paper Support

[AutoSchemaKG](https://arxiv.org/html/2505.23628v1) shows that autonomous schema
induction is possible at large scale, but DREAM should still treat schema
changes as reviewable. Engineering schemas affect trust, retrieval, and review
workflow.

### DREAM Implication

DREAM can suggest schema evolution, but durable schema changes should require
human approval.

## Principle 8: Treat Generated Artifacts as Views, Not Sources of Truth

DREAM can generate:

- wiki pages
- architecture maps
- runbook indexes
- decision logs
- PR review context
- requirement impact maps
- audit reports

But generated artifacts should not automatically become new memory sources. They
are views over source-backed memory. If generated text is re-ingested without
original evidence, feedback loops can amplify errors.

## Principle 9: Validate Before Promotion

Every candidate memory should pass validation before it becomes durable memory.

Required gates:

1. Evidence gate: exact source span is required.
2. Schema gate: claim must fit approved node and edge types.
3. Freshness gate: source must not be stale relative to current code.
4. Conflict gate: conflicting claims are preserved, not collapsed.
5. Entity-resolution gate: canonical entity must be known or reviewed.
6. Security gate: secrets, PII, and sensitive operational data must be blocked.
7. Abstention gate: extractor can output `INSUFFICIENT_EVIDENCE`.
8. Human gate: high-risk claims require review.

### Failure Evidence

A [mem0 production audit issue](https://github.com/mem0ai/mem0/issues/4573)
reported that 97.8% of 10,134 extracted memory entries were junk. The failure
categories included duplicates, transient task state, system architecture dumps,
hallucinated profiles, and sensitive leakage. This is a strong warning against
automatic durable memory writes.

[OpenAI's hallucination analysis](https://openai.com/index/why-language-models-hallucinate/)
also supports rewarding abstention instead of guessing. DREAM evals should
penalize confident unsupported claims and reward correct refusal to create
memory.

## Principle 10: Evaluate the Pipeline, Not Only the Answers

DREAM should evaluate each stage:

| Stage | Evaluation |
| --- | --- |
| Ingestion | source coverage, parse errors, permissions, skipped files |
| Structure extraction | symbol precision, dependency accuracy, test mapping accuracy |
| Semantic extraction | claim precision, unsupported claim rate, condition accuracy |
| Entity resolution | merge precision, split recall, canonical naming stability |
| Retrieval | context precision, context recall, evidence path correctness |
| Answering | grounded correctness, citation coverage, abstention quality |
| Incremental update | update recall, stale detection recall, regeneration cost |
| Review | review time, approval rate, reviewer disagreement, escaped defects |
| Security | secret leakage rate, sensitive-source filtering, policy violations |

### Evaluation References

- [OpenAI Evals guide](https://developers.openai.com/api/docs/guides/evals)
- [RepoDocBench](https://arxiv.org/html/2604.26523v1)
- [CodeWikiBench](https://arxiv.org/abs/2510.24428)
- [GraphRAG-Bench](https://arxiv.org/html/2506.02404v2)
- [RAG evaluation survey](https://arxiv.org/html/2504.20119v2)
- [LLM-as-a-Judge survey](https://arxiv.org/html/2411.15594v6)

## Practical DREAM Build Plan

### Phase 1: Evidence-Backed Candidate Memory

Deliver:

- ingest repo + docs + runbooks
- generate source-backed candidate claims
- build lightweight evidence graph paths
- show review queue for candidate memory diffs
- reject unsupported claims

Exit criteria:

- every memory has source evidence
- unsupported claim rate is measured
- reviewer can approve/reject/deprecate a memory

### Phase 2: Deterministic RepoGraph

Deliver:

- parse symbols, imports, tests, endpoints, jobs
- build structural graph
- link docs and runbooks to code entities
- support impact mapping from requirement to code/test/docs

Exit criteria:

- graph answers basic structural questions without LLM inference
- evidence paths connect concepts to code and tests

### Phase 3: Temporal Memory

Deliver:

- valid-from and valid-until facts
- stale detection
- superseded facts
- conflict handling
- source priority rules

Exit criteria:

- old runbook claims can be marked stale
- PR or code changes trigger affected memory candidates

### Phase 4: Incremental Update

Deliver:

- git diff-triggered re-index
- semantic impact propagation
- selective regeneration
- "what changed" memory report

Exit criteria:

- changed files trigger affected memory/wiki updates
- unchanged areas are not fully regenerated
- update recall is measured

### Phase 5: Evaluation Harness

Deliver:

- golden repo and docs fixtures
- stale docs fixture
- conflicting runbook fixture
- fake citation fixture
- entity collision fixture
- secret leakage fixture

Exit criteria:

- extraction precision is measured
- unsupported claim rate is measured
- stale detection recall is measured
- review burden is measured

## Recommended Internal Positioning

DREAM should be described as:

> A source-grounded engineering memory platform that turns repositories,
> documentation, runbooks, incidents, and historical work records into
> reviewable, incrementally maintained memory for AI-assisted engineering
> workflows.

It should not be described as:

- a generic chatbot
- a plain RAG wrapper
- a one-time documentation generator
- an auto-memory system that silently writes facts

## Source Appendix

### Core Papers and Benchmarks

- RepoDoc: https://arxiv.org/html/2604.26523v1
- CodeWiki: https://arxiv.org/abs/2510.24428
- Zep temporal KG: https://arxiv.org/html/2501.13956v1
- GraphRAG-Bench: https://arxiv.org/html/2506.02404v2
- AutoSchemaKG: https://arxiv.org/html/2505.23628v1
- RAG evaluation survey: https://arxiv.org/html/2504.20119v2
- LLM-as-a-Judge survey: https://arxiv.org/html/2411.15594v6

### Reference Systems

- CodeWiki GitHub: https://github.com/FSoft-AI4Code/CodeWiki
- DeepWiki docs: https://docs.devin.ai/work-with-devin/deepwiki
- Google Code Wiki: https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/
- Graphiti: https://github.com/getzep/graphiti
- Cognee: https://github.com/topoteretes/cognee
- Microsoft GraphRAG: https://microsoft.github.io/graphrag/
- CocoIndex: https://cocoindex.io/
- Neo4j LLM Graph Builder: https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/

### Risk and Validation Evidence

- mem0 production memory audit: https://github.com/mem0ai/mem0/issues/4573
- LangChain citation issue: https://github.com/langchain-ai/langchain/issues/7239
- OpenAI Evals guide: https://developers.openai.com/api/docs/guides/evals
- OpenAI hallucination analysis: https://openai.com/index/why-language-models-hallucinate/

## Final Methodological Thesis

The frontier methodology is not "store more context." It is:

```text
extract less, cite everything, validate before promotion, preserve conflict,
track time, regenerate selectively, and make human review cheap.
```

DREAM should build around that thesis.
