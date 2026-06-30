<!-- SPDX-License-Identifier: Apache-2.0 -->

# Market and Technical Evidence for DREAM Engineering Memory Systems

Research date: 2026-06-23

## Executive Summary

Public research and open-source activity show clear demand for systems that turn
repositories, documentation, runbooks, incidents, and historical work records
into durable AI context. However, the current landscape is fragmented:

1. Repo-to-wiki systems automate codebase documentation.
2. GraphRAG and AI memory systems build knowledge graphs and long-term memory.
3. Enterprise context graphs connect work artifacts across SaaS systems.

No reviewed open-source project appears to provide the full DREAM loop:

```text
git repo + runbooks + arbitrary docs + incidents + PR history
  -> automated extraction
  -> source-grounded engineering memory
  -> incremental maintenance
  -> validation and evaluation
  -> human review gates
  -> durable memory promotion
```

This creates a clear product and research opportunity for DREAM: combine
deterministic repository analysis, LLM-based semantic extraction, temporal
knowledge graph memory, source-linked wiki generation, and reviewable memory
diffs.

## Research Method

The conclusion was cross-checked through three independent research passes and
one red-team pass focused on failure modes. The passes independently converged
on the same strategic pattern:

- Repo wiki products are strong at onboarding and code understanding.
- AI memory and GraphRAG frameworks are strong at graph-based retrieval and
  long-term context.
- The missing layer is governed engineering memory: source-linked, diff-aware,
  incrementally maintained, and human-reviewable.

## Landscape Map

### 1. Repo to Living Wiki / Documentation

These projects are closest to DREAM's repository understanding surface. They
usually ingest source code and generate structured documentation, diagrams, and
source-linked explanations.

| Project | Evidence | Relevance to DREAM | Gap |
| --- | --- | --- | --- |
| [CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki) | Open-source framework for automated repository-level documentation; supports architecture-aware documentation, cross-module interactions, diagrams, and multiple languages. Paper: [CodeWiki](https://arxiv.org/abs/2510.24428). | Strongest open-source reference for repo-to-wiki automation and benchmark-driven evaluation. | Focuses on code documentation, not durable engineering memory governance. |
| [DeepWiki / Devin Wiki](https://docs.devin.ai/work-with-devin/deepwiki) | Automatically indexes repositories, creates wiki pages, architecture diagrams, source links, and Ask Devin grounding. | Strong commercial product pattern for source-linked codebase understanding. | Closed-source; public docs do not expose rigorous memory promotion or review gates. |
| [Google Code Wiki](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/) | Google describes a system that scans a full codebase, regenerates after changes, powers chat with wiki context, and generates architecture/class/sequence diagrams. | Strong evidence that the market values continuously updated code understanding. | Closed-source public preview; mainly code repository focused. |
| [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open) | Open-source repo-to-wiki and diagram generation inspired by DeepWiki. | Useful as a reference for demo UX and repo documentation generation. | Weak evaluation, governance, and memory lifecycle story. |

### 2. AI Memory / GraphRAG / Knowledge Graph Substrates

These systems provide the building blocks for durable memory, graph extraction,
temporal context, and hybrid retrieval.

| Project | Evidence | Relevance to DREAM | Gap |
| --- | --- | --- | --- |
| [Graphiti](https://github.com/getzep/graphiti) | Open-source temporal context graph engine for AI agents. Tracks facts over time, preserves provenance, supports incremental updates, and queries temporal relationships. | Strong reference for evolving engineering facts, stale knowledge, provenance, and fact invalidation. | Not a repo/runbook-specific memory product. |
| [Cognee](https://github.com/topoteretes/cognee) | Open-source AI memory platform with self-hosted knowledge graph memory, graph and vector retrieval, and arbitrary data ingestion. | Strong reference for general agent memory and graph memory infrastructure. | DREAM still needs engineering-specific extraction, eval, and review workflows. |
| [Microsoft GraphRAG](https://microsoft.github.io/graphrag/) | Extracts entities, relationships, claims, and community summaries from raw text for GraphRAG retrieval. | Useful for corpus-level summarization and cross-document sensemaking. | Batch-oriented; dynamic engineering memory and review gates are not core. |
| [CocoIndex](https://cocoindex.io/) | Incremental data framework for AI agents; supports source tracking and incremental processing. | Useful substrate for DREAM's diff-aware ingest and re-index pipeline. | Framework layer, not an end-user engineering memory system. |
| [Neo4j LLM Graph Builder](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/) | LLM-based extraction into Neo4j with node and relationship schema control. | Good reference for schema-guided extraction and visual graph inspection. | Projectized graph building, not full memory lifecycle governance. |
| [LightRAG](https://lightrag.github.io/) | Graph-based RAG with document graph extraction and dual-level retrieval. | Useful for graph-augmented retrieval patterns. | Limited human review, deletion, conflict, and governance story. |

### 3. Enterprise Context Graphs and Connectors

These products validate the enterprise need for permission-aware organizational
context across repositories, docs, tickets, chats, and tools.

| Product | Evidence | Relevance to DREAM | Gap |
| --- | --- | --- | --- |
| [Glean Connectors](https://docs.glean.com/connectors/connectors-power-glean) and [Glean GitHub Connector](https://www.glean.com/connectors/github) | Connectors synchronize enterprise content and metadata into search and graph context. | Shows the importance of connectors, ACLs, metadata, and enterprise identity context. | Commercial search/agent platform; not open-source engineering memory. |
| [Atlassian Teamwork Graph](https://www.atlassian.com/platform/teamwork-graph) and [Rovo](https://www.atlassian.com/blog/company-news/teamwork-graph-team-26) | Connects Jira, Confluence, Bitbucket, Loom, and other work artifacts into a teamwork graph. | Validates an engineering work graph spanning code, tickets, docs, incidents, and ownership. | Atlassian ecosystem; extraction quality and governance internals are opaque. |
| [Microsoft 365 Copilot Connectors](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/connectors-gallery-partners) and [GitHub Knowledge Connector](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/github-cloud-knowledge-overview) | Brings external sources into Microsoft Search and Copilot with permissions and citations. | Shows that runbooks, technical notes, markdown docs, and GitHub content are valuable enterprise AI context. | Connector/search layer, not source-grounded engineering memory extraction. |

## Cross-Validated Findings

### Finding 1: The closest public systems cover only part of DREAM

CodeWiki, DeepWiki, and Google Code Wiki validate the repo-to-living-wiki
direction. Graphiti, Cognee, GraphRAG, and CocoIndex validate durable graph memory
and retrieval infrastructure. None of them provide the full governed engineering
memory lifecycle by themselves.

### Finding 2: DREAM should not be positioned as generic RAG

Generic RAG answers questions over documents. DREAM's stronger position is:

```text
source-grounded engineering memory generated from repo, docs, runbooks,
incidents, and PR history, with reviewable memory diffs and durable promotion
gates.
```

### Finding 3: The core product unit should be an atomic candidate memory

The durable memory object should not be a free-form LLM summary. It should be an
atomic claim with evidence:

```text
entity
relation
value
condition
confidence
source_type
repo
file_path
line_range
commit_sha
evidence_span
extracted_at
review_status
```

### Finding 4: Human review is not optional

Public failure evidence shows that automatic memory extraction can write junk,
duplicate memories, transient state, hallucinated facts, or sensitive details
into long-term memory. For example, one mem0 production audit reported that
97.8% of 10,134 extracted memories were junk:

- [mem0 issue #4573](https://github.com/mem0ai/mem0/issues/4573)

This does not invalidate AI memory systems. It means DREAM should default to
candidate memory diffs and promote only reviewed, source-backed, fresh, and
entity-resolved claims.

## Why This Supports DREAM

### Market Need

The number of active projects and commercial products in repo documentation,
GraphRAG, agent memory, and enterprise context graphs indicates clear demand for
better AI context systems. Existing tools validate the problem from multiple
angles:

- Developers need automatic repository understanding.
- Agents need persistent memory beyond one prompt window.
- Enterprises need permission-aware connectors and source-grounded answers.
- Teams need docs and runbooks that stay current with code and incidents.

### Technical Gap

The missing technical layer is governed engineering memory:

- deterministic repo graph extraction
- semantic knowledge extraction from docs and runbooks
- temporal fact validity and invalidation
- source-linked generated wiki pages
- incremental update propagation
- reviewable memory diffs
- extraction and retrieval evals
- human approval gates for high-risk memory

### DREAM Differentiation

DREAM can differentiate by making four commitments:

1. Every memory is source-linked.
2. Every update is diff-aware.
3. Every risky extraction is reviewable.
4. Every artifact is both agent-readable and human-readable.

## Proposed DREAM Architecture Direction

### Layer 1: Source Ingestion

Inputs:

- Git repositories
- README and markdown documentation
- Runbooks
- ADRs and design docs
- Incidents and postmortems
- PRs and issues
- CI, workflow, Kubernetes, Terraform, and deployment metadata

Required source metadata:

- repository identifier
- commit SHA
- file path
- line range or document span
- source type
- extracted timestamp
- access policy or source trust level

### Layer 2: Deterministic RepoGraph

Use AST, Tree-sitter, LSP, or language-specific parsers to extract:

- packages and modules
- classes, functions, methods
- imports and dependencies
- endpoints, jobs, tasks, CLI commands
- tests and test mappings
- ownership and path conventions where available

This layer should not depend on LLM inference for basic structural truth.

### Layer 3: Semantic KnowledgeGraph

Use LLM extraction for engineering semantics:

- domain concepts
- decisions
- risks
- runbook steps
- incident lessons
- operational constraints
- architecture assumptions
- known failure modes
- review rules

Each extracted claim must link back to deterministic evidence.

### Layer 4: Generated Artifacts

Generate:

- source-linked wiki pages
- architecture map
- runbook index
- decision log
- incident memory
- PR review context
- requirement impact maps
- "what changed since last scan" summaries

Generated artifacts must not become authoritative sources unless backed by
original evidence.

### Layer 5: Review and Promotion

DREAM should treat extraction output as a reviewable diff:

- add fact
- update fact
- deprecate fact
- merge entity
- split entity
- mark stale
- flag conflict
- update wiki section

Only reviewed or low-risk auto-approved claims should enter durable memory.

## Acceptance and Evaluation Plan

### Required Evaluation Dimensions

| Dimension | What to Measure |
| --- | --- |
| Source coverage | Percentage of repo/docs/runbooks/incidents represented with traceable source spans. |
| Extraction precision | Fraction of extracted claims that are correct and useful. |
| Unsupported claim rate | Fraction of claims without sufficient source support. |
| Entity resolution precision | Correctness of merges and splits for services, classes, APIs, jobs, and runbooks. |
| Stale detection recall | Ability to flag outdated docs or runbooks after code changes. |
| Conflict handling | Whether conflicting sources are preserved as conflicts instead of collapsed into a false conclusion. |
| Grounded answer correctness | Whether answers cite the correct source and avoid unsupported claims. |
| Incremental update recall | Whether changed files correctly trigger affected memory and wiki updates. |
| Review burden | Human time required per accepted memory change. |
| Security filtering | Ability to prevent secrets, PII, internal URLs, and sensitive commands from entering durable memory. |

### Golden Test Set

The initial DREAM evaluation dataset should include synthetic and real-like
fixtures covering:

- stale runbook references
- renamed classes and moved files
- deleted endpoints
- conflicting README and code behavior
- duplicate service names
- fake or weak citations
- transient incident notes
- deployment-sensitive commands
- secrets and internal identifiers
- old PR decisions superseded by newer code

### Evaluation References

Useful public references:

- [OpenAI Evals guide](https://developers.openai.com/api/docs/guides/evals)
- [Why language models hallucinate](https://openai.com/index/why-language-models-hallucinate/)
- [GraphRAG-Bench](https://arxiv.org/html/2506.02404v2)
- [CodeWiki paper](https://arxiv.org/abs/2510.24428)
- [RepoDoc / RepoDocBench](https://arxiv.org/html/2604.26523v1)

## Human Review Gates

DREAM should require human review for:

1. Schema or ontology changes.
2. Low-confidence extraction.
3. Conflicting source evidence.
4. Stale or possibly outdated documentation.
5. Entity merge or split decisions.
6. Security, compliance, deployment, production, or customer-impacting facts.
7. Owner, permission, or escalation-path claims.
8. Durable promotion of generated summaries.
9. Any claim whose source is generated by DREAM rather than an original artifact.

Low-risk memories can be auto-approved only when:

- evidence is exact and source-linked
- source priority is high
- no conflict is detected
- entity resolution is unambiguous
- security filtering passes
- the claim fits an approved schema

## Red-Team Risks

| Risk | Failure Mode | DREAM Mitigation |
| --- | --- | --- |
| Hallucinated memory | LLM infers facts that are not in source material. | Require exact evidence span and allow abstention. |
| Stale docs | Old runbooks or README content contradict current code. | Freshness checks and stale candidate flags. |
| Fake citations | Model invents file paths, URLs, or source names. | System-generated citations only; model cannot author evidence IDs. |
| Entity split/merge errors | Same service becomes many nodes or different services are merged. | Canonical entity resolver plus review queue. |
| Conflict collapse | Conflicting evidence is summarized into one false conclusion. | Preserve conflict status and require owner review. |
| Transient state pollution | Temporary task state becomes durable memory. | Source type rules and memory promotion policy. |
| Feedback-loop amplification | Generated memory is re-extracted as new memory. | No self-extraction without original evidence. |
| Eval optimism | LLM judges approve weak extraction. | Golden sets, deterministic checks, and human spot checks. |
| Review overload | Too many diffs cause reviewers to skim. | Risk-prioritized queues and review budget metrics. |
| Security leakage | Secrets or sensitive operational data enter memory. | Redaction, deny lists, and source trust policies. |

## Source Appendix

### Repo Wiki and Code Understanding

- CodeWiki GitHub: https://github.com/FSoft-AI4Code/CodeWiki
- CodeWiki paper: https://arxiv.org/abs/2510.24428
- Devin DeepWiki docs: https://docs.devin.ai/work-with-devin/deepwiki
- Google Code Wiki blog: https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/
- DeepWiki-Open: https://github.com/AsyncFuncAI/deepwiki-open

### AI Memory, Knowledge Graph, and GraphRAG

- Graphiti: https://github.com/getzep/graphiti
- Zep temporal KG paper: https://arxiv.org/html/2501.13956v1
- Cognee: https://github.com/topoteretes/cognee
- Microsoft GraphRAG: https://microsoft.github.io/graphrag/
- GraphRAG-Bench: https://arxiv.org/html/2506.02404v2
- CocoIndex: https://cocoindex.io/
- CocoIndex docs KG example: https://cocoindex.io/blogs/knowledge-graph-for-docs/
- Neo4j LLM Graph Builder: https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/
- Neo4j LLM Graph Builder release blog: https://neo4j.com/blog/developer/llm-knowledge-graph-builder-release/
- LightRAG: https://lightrag.github.io/

### Enterprise Context Graphs and Connectors

- Glean connectors: https://docs.glean.com/connectors/connectors-power-glean
- Glean GitHub connector: https://www.glean.com/connectors/github
- Atlassian Teamwork Graph: https://www.atlassian.com/platform/teamwork-graph
- Atlassian Teamwork Graph blog: https://www.atlassian.com/blog/company-news/teamwork-graph-team-26
- Microsoft 365 Copilot connector gallery: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/connectors-gallery-partners
- Microsoft GitHub Knowledge connector: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/github-cloud-knowledge-overview

### Evaluation, Risks, and Human Review

- OpenAI Evals guide: https://developers.openai.com/api/docs/guides/evals
- OpenAI hallucination analysis: https://openai.com/index/why-language-models-hallucinate/
- mem0 production memory audit issue: https://github.com/mem0ai/mem0/issues/4573
- LangChain citation issue: https://github.com/langchain-ai/langchain/issues/7239
- API documentation and LLM failure paper: https://arxiv.org/html/2503.15231v1
- DOCER stale documentation paper: https://link.springer.com/article/10.1007/s10664-023-10397-6
- RAG evaluation survey: https://arxiv.org/html/2504.20119v2
- LLM-as-a-Judge survey: https://arxiv.org/html/2411.15594v6

## Recommended Internal Decision

DREAM should proceed as an engineering memory platform, not a generic chatbot or
plain RAG application.

The initial project milestone should prove:

1. automatic extraction from repo and docs into source-backed candidate memories
2. evidence graph paths across code, docs, incidents, Jira/PR-like history, and
   tests
3. reviewable memory diffs
4. stale/conflict detection
5. a small but explicit evaluation suite
6. human approval gates for durable memory promotion

This scope is narrow enough to build, but differentiated enough to avoid being a
commodity wrapper around vector search or repo wiki generation.
