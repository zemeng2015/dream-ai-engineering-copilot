<!-- SPDX-License-Identifier: Apache-2.0 -->

# ChatGPT Review Brief: Should DREAM Build an Automated Memory Extraction System?

This brief is intended to be submitted to ChatGPT together with:

- `docs/research-ai-engineering-memory-systems.md`
- `docs/dream-frontier-methodology.md`

The goal is to obtain an independent strategic and technical critique of whether
DREAM should build a repo/document/runbook-to-engineering-memory extraction and
knowledge distillation system, and if so, how it should be scoped.

## Decision Question

We are evaluating whether DREAM should become an automated engineering memory
system:

> Given a repository, Git history or PRs, runbooks, design documents, incidents,
> tickets, and arbitrary team documents, DREAM would extract, organize, validate,
> and continuously maintain a source-grounded memory / knowledge graph that can
> support requirement analysis, PR review, code generation, test generation, and
> onboarding.

Please analyze:

1. Whether this is worth building as a core product direction.
2. Whether it is differentiated from existing systems.
3. What the minimum credible MVP should be.
4. Where automation should stop and human review should begin.
5. How memory extraction and knowledge distillation should be evaluated.
6. What risks would make this fail technically, operationally, or commercially.

## Current DREAM Implementation Snapshot

DREAM already has a lightweight memory layer, but it is not yet a full automatic
memory extraction and knowledge distillation system.

Current capabilities:

- Structured team knowledge packs loaded from local Markdown documents.
- Heading-based document chunking and deterministic keyword retrieval.
- Codebase indexing for Java, Python, and TypeScript repositories.
- File, role, language, symbol, endpoint-like method, dependency, concept, and
  source-to-test mapping extraction.
- Evidence Graph Lite that links concepts, docs, incidents, historical Jira,
  historical PRs, code files, symbols, and tests.
- Requirement-case analysis that retrieves knowledge, codebase, and graph
  evidence before producing impact maps, clarification questions, briefs, and
  Jira drafts.
- PR review flow that can use changed files to pull related codebase and graph
  evidence.
- Audit records with input hashes, retrieved source paths, model provider/name,
  output paths, warnings, and status.
- Evaluation heuristics for evidence coverage across domain docs, architecture,
  runbooks, incidents, historical Jira, historical PRs, concept memory, code
  files, test files, and evidence graph usage.

Current limitations:

- Retrieval is deterministic keyword matching, not embeddings, reranking, or
  graph-aware neural retrieval.
- The graph is built mostly from front matter and deterministic code extraction,
  not from LLM-extracted atomic claims.
- There is no durable memory lifecycle with candidate claims, validation,
  approval, supersession, expiry, or conflict handling.
- There is no schema-guided claim extraction pipeline.
- There is no human review queue for high-risk memory writes.
- There is no dedicated benchmark for memory extraction precision/recall,
  unsupported claim rate, conflict detection, or stale memory detection.
- There is no automatic ingestion from Git history, live PRs, Confluence, Jira,
  Slack, or incident systems.
- Generated artifacts are not promoted back into durable memory, which avoids
  feedback loops but also means memory does not improve automatically.

## Relevant Implementation Files

Memory composition:

- `dream/memory/retriever.py`

Knowledge layer:

- `dream/knowledge/models.py`
- `dream/knowledge/pack_loader.py`
- `dream/knowledge/markdown_loader.py`
- `dream/knowledge/chunker.py`
- `dream/knowledge/retriever.py`
- `docs/knowledge-packs.md`

Codebase memory:

- `dream/codebase/indexer.py`
- `dream/codebase/models.py`
- `dream/codebase/scanner.py`
- `dream/codebase/retriever.py`
- `docs/codebase-memory.md`

Evidence graph:

- `dream/graph/models.py`
- `dream/graph/builder.py`
- `dream/graph/retriever.py`
- `docs/evidence-graph.md`

Integration and evaluation:

- `dream/requirement_cases/service.py`
- `dream/api/routes.py`
- `dream/audit/logger.py`
- `dream/evals/evidence.py`
- `tests/test_codebase_memory.py`
- `tests/test_evidence_graph.py`

## Architecture Summary

### Knowledge Packs

Team memory starts from `knowledge_packs/<team_id>/team.yaml`, which declares
document paths, repositories, applications, review rules, requirement templates,
and test-generation rules.

Markdown files can carry front matter such as:

```yaml
---
app: BatchJobDemo
component: job-execution
doc_type: domain
---
```

`MarkdownDocumentLoader`:

- resolves configured document directories safely within the pack root
- strips leading HTML comments
- reads YAML front matter
- infers document type from path
- extracts the first H1 as title
- creates stable document IDs from source paths

`Chunker` splits documents by Markdown headings up to H3. `SimpleRetriever` then
scores chunks with deterministic token matching, giving title matches higher
weight than body matches.

### Codebase Memory

`CodebaseIndexer` scans a repository, ignoring common generated or dependency
directories such as `.git`, `.venv`, `node_modules`, `target`, `build`, `dist`,
cache directories, and `__pycache__`.

It detects file language and role, then extracts symbols and dependencies for
Java, Python, and TypeScript. It also derives concepts from file paths, symbols,
and repeated domain tokens. It maps tests to source files using basename
similarity.

The generated `RepoIndex` contains:

- file nodes
- symbol nodes
- dependency edges
- source-to-test mappings
- concept mappings
- summary
- warnings

Artifacts are stored under `artifacts/codebase-indexes/{team_id}/{repo_name}.json`.

### Engineering Memory Retriever

`EngineeringMemoryRetriever.search(...)` combines three evidence sources:

1. Knowledge pack search
2. Codebase index search
3. Evidence graph search

It expands certain queries with known domain-specific terms, deduplicates
results, then selects a balanced top-k across incidents, historical Jira,
historical PRs, architecture docs, domain docs, testing docs, concept memory,
graph evidence, code files, symbols, and test files.

This is intentionally lightweight and predictable, but it is not yet a general
semantic memory extraction system.

### Evidence Graph Lite

The evidence graph stores:

- concept nodes
- knowledge document nodes
- incidents
- historical Jira
- historical PRs
- concept memory documents
- architecture/domain/testing/runbook docs
- code files
- code symbols
- test files

The graph supports these edge types:

- `MENTIONED_IN`
- `IMPLEMENTED_BY`
- `TESTED_BY`
- `REGRESSED_BY`
- `REQUIRED_BY`
- `CHANGED_BY`
- `AFFECTS`
- `DEFINED_IN`
- `RELATED_TO`

The builder uses:

- Markdown front matter: `concepts`, `related_code`, `related_jira`,
  `related_pr`, `related_incidents`, `related_docs`
- codebase file/symbol/concept/test mappings
- stable IDs and alias resolution
- deterministic path traversal protection

The retriever:

- scores graph nodes by query token overlap
- expands one-hop neighbors
- returns evidence paths such as:

```text
execution status -> StatusTracker.java -> StatusTrackerTest.java -> INC-103 -> DFP-101 -> PR-502
```

The graph is useful for explainability, but it is currently a curated metadata
graph rather than an automatically distilled memory graph.

### Requirement and Review Workflows

`RequirementCaseService.analyze_case(...)` retrieves memory evidence, produces
impact items and clarification questions, then logs an audit record with
retrieved source paths.

PR review tests show that when a PR changes `OutputCollector.java`, DREAM can
surface related memory such as:

- `OutputCollector.java`
- duplicate output incident memory
- DFP-110 output collection idempotency Jira
- PR-508 output collection idempotency
- `OutputCollectorTest.java`

This demonstrates the intended product loop: user input or code change ->
retrieved evidence -> analysis/generation -> audit/evaluation.

## Key Code Evidence

### EngineeringMemoryRetriever composition

```python
class EngineeringMemoryRetriever:
    def search(...):
        evidence = []
        for knowledge_query in self._knowledge_queries(query):
            evidence.extend(self._search_knowledge(...))

        repo_names = [repo_name] if repo_name else self.codebase_repository.list_repo_names(team_id)
        for candidate_repo in repo_names:
            for code_query in self._code_queries(query):
                results.extend(self.codebase_retriever.search(...))
            evidence.append(ContextEvidence(...))

        evidence.sort(...)
        evidence.extend(self._search_graph(...))
        evidence.sort(...)
        evidence = self._dedupe(evidence)
        return self._balanced_top_k(evidence, top_k)
```

### Codebase index model

```python
class RepoIndex(BaseModel):
    repo_id: str
    repo_name: str
    repo_path: str
    team_id: str
    indexed_at: str
    files: list[FileNode]
    symbols: list[SymbolNode]
    tests: list[TestMapping]
    dependencies: list[DependencyEdge]
    concepts: list[ConceptMapping]
    summary: str
    warnings: list[str]
```

### Evidence graph model

```python
class EvidenceNode(BaseModel):
    node_id: str
    node_type: str
    key: str
    title: str
    source_path: str | None = None
    aliases: list[str]
    concepts: list[str]
    metadata: dict[str, object]

class EvidenceEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    confidence: float
    reason: str
```

### Evidence graph builder behavior

```python
for entry in doc_entries:
    doc_node = add_node(EvidenceNode(...))
    for concept in doc_node.concepts:
        concept_node = add_node(self._concept_node(team_id, concept))
        add_edge(
            concept_node.node_id,
            doc_node.node_id,
            "MENTIONED_IN",
            0.85,
            "Document front matter lists this concept.",
        )

if repo_index is not None:
    self._add_codebase_nodes(repo_index, add_node, add_edge)

for entry in doc_entries:
    for code_path in self._metadata_list(entry.metadata.get("related_code")):
        code_node = self._resolve_or_stub_code_node(...)
        add_edge(doc_node_id, code_node.node_id, "AFFECTS", 0.8, ...)
```

### Evidence coverage evaluation

```python
coverage = {
    "domain_docs": ...,
    "architecture_docs": ...,
    "runbooks": ...,
    "incidents": ...,
    "historical_jira": ...,
    "historical_pr": ...,
    "testing_docs": ...,
    "concept_memory": ...,
    "code_files": ...,
    "test_files": ...,
}
if "evidence graph" or "graph_" or "--implemented_by-->" in text:
    coverage["evidence_graph"] = True
```

## Existing Tests That Demonstrate the Memory Layer

`tests/test_codebase_memory.py` verifies:

- scanner ignores dependency/generated directories
- Java extractor detects classes, methods, and endpoint-like annotations
- codebase indexer writes JSON and maps tests
- codebase retriever finds relevant source files

`tests/test_evidence_graph.py` verifies:

- graph builder writes nodes, edges, and JSON
- graph contains concepts, code files, incidents, and historical work
- graph search explains `execution status`
- document path traversal is rejected
- requirement analysis uses graph evidence
- PR review uses evidence graph for changed files and historical risks

## What We Want ChatGPT To Produce

Please provide a candid product and architecture recommendation:

1. Decision: build / do not build / build only a narrow MVP.
2. Differentiation: what should DREAM do that generic RAG, DeepWiki-like tools,
   GraphRAG stacks, or memory frameworks do not already solve?
3. MVP scope: exact ingestion sources, extraction schema, validation gates,
   reviewer workflow, and output surfaces.
4. Technical architecture: pipeline stages, storage model, graph model,
   retrieval strategy, update strategy, and eval harness.
5. Automation boundaries: which memory claims can be auto-promoted, which need
   human review, and which should never become durable memory.
6. Evaluation: metrics, golden datasets, red-team tests, acceptance thresholds,
   and rollout gates.
7. Risk register: hallucination, stale memory, IP/privacy, user trust,
   maintenance cost, enterprise adoption, and false differentiation.
8. Roadmap: 2-week, 6-week, and 12-week plan for DREAM.

Please be concrete. Prefer mechanisms, schemas, gates, and experiments over
generic encouragement.
