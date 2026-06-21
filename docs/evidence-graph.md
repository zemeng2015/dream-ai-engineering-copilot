<!-- SPDX-License-Identifier: Apache-2.0 -->

# Evidence Graph Lite

DREAM Evidence Graph Lite links team memory into explainable evidence paths. It
is the layer between simple keyword retrieval and a future full code graph.

The graph answers questions such as:

- Which docs, code files, tests, incidents, Jira stories, and PRs relate to execution status?
- If a PR changes `OutputCollector.java`, which historical risks should reviewers see?
- Did an Engineering Brief cite the expected sources for a known scenario?

## What It Stores

Nodes:

- concepts such as execution status, output collection, partial recovery
- Markdown docs from the team knowledge pack
- incidents such as INC-103 status stuck RUNNING
- historical Jira such as DFP-110 output collection idempotency
- historical PRs such as PR-508 output collection idempotency
- code files and symbols from the codebase index
- test files and source-to-test mappings

Edges:

- `MENTIONED_IN`
- `IMPLEMENTED_BY`
- `TESTED_BY`
- `REGRESSED_BY`
- `REQUIRED_BY`
- `CHANGED_BY`
- `AFFECTS`
- `DEFINED_IN`

## Why It Is Lite

The MVP does not attempt a full AST call graph, runtime dependency graph, cloud
execution graph, or graph database. It uses deterministic metadata and codebase
index relationships:

- Markdown front matter such as `concepts`, `related_code`, `related_jira`,
  `related_pr`, and `related_incidents`
- codebase file, symbol, concept, and source-to-test mappings
- historical Jira / PR / incident memory docs
- concept memory docs

This keeps maintenance cost low while making the demo much more credible than
plain RAG.

## Commands

```bash
dream codebase index \
  --team demo_team \
  --repo examples/dfp-demo-repo \
  --name dfp-demo-repo

dream graph build \
  --team demo_team \
  --repo dfp-demo-repo

dream graph search \
  --team demo_team \
  --repo dfp-demo-repo \
  --query "execution status"

dream graph explain \
  --team demo_team \
  --repo dfp-demo-repo \
  --concept "execution status"

dream graph neighbors \
  --team demo_team \
  --repo dfp-demo-repo \
  --node backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java
```

## Example

For the query `execution status`, the graph can expand to:

```text
execution status
 -> status-tracking-design.md
 -> StatusTracker.java
 -> StatusTrackerTest.java
 -> INC-103 status stuck RUNNING
 -> DFP-101 add execution status tracking
 -> PR-502 execution status polling
```

For a PR touching `OutputCollector.java`, the graph can surface:

```text
OutputCollector.java
 -> output collection
 -> INC-102 duplicate output
 -> DFP-110 output collection idempotency
 -> PR-508 output collection idempotency
 -> OutputCollectorTest.java
```

## Workflow Integration

Requirement Case analysis uses graph evidence when a graph exists. PR Review
uses changed files to find graph neighbors and related historical risks.
Evaluation can detect graph-backed outputs through source coverage.
