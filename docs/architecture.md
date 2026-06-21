<!-- SPDX-License-Identifier: Apache-2.0 -->

# Architecture

DREAM is a small Python platform for reusable, codebase-aware AI-assisted
engineering workflows. The core package owns configuration, path safety,
artifacts, and shared errors.

## Core Platform

The platform exposes a Typer CLI and FastAPI app. Both call the same service
classes, so local demos and API workflows produce the same artifacts and audit
records.

## Knowledge Pack

A knowledge pack combines `team.yaml` with Markdown files. Markdown documents are
loaded, chunked by headings, tagged with metadata, and searched by
`SimpleRetriever`.

## Codebase Memory Index

The codebase package scans local repositories and writes JSON indexes under
`artifacts/codebase-indexes/`. The index stores file nodes, symbol nodes,
source-to-test mappings, simple dependency edges, concept mappings, summaries,
and warnings.

## Engineering Memory Retriever

`EngineeringMemoryRetriever` combines knowledge pack retrieval and codebase
memory retrieval. It is the seam for future vector retrieval or code graph
improvements, but Phase 2 remains deterministic and lightweight.

## Requirement Case Workflow

Requirement Cases turn rough requests into structured analysis: retrieved
context, impact map, role-specific questions, engineering brief, Jira draft, and
audit trail.

## Workflow Plugins

Requirement drafting, PR review summaries, and test-generation providers are
separate workflow modules. The MVP uses deterministic mock behavior by default.

The PR review assistant can use codebase memory when a repo index is available.
It falls back to document and diff context if no index exists.

## Audit and Eval

Generation runs write audit records to SQLite. Human ratings are stored in the
same database so teams can compare usefulness and correctness over time.

The Evaluation Agent is a first-class workflow. It reads artifacts, audit runs,
or Requirement Case snapshots and produces scorecards for completeness,
evidence quality, impact accuracy, role coverage, test awareness, historical
context, actionability, specificity, and hallucination risk. DemoCorp eval
profiles provide golden expectations for common scenarios such as async status
tracking, partial recovery, output idempotency, large output preview, config
validation, operator retry, and workflow versioning.

## TestGen Interface

DREAM does not implement a production test generator. It defines
`TestGenProvider` so external tools can plug in behind a stable plan/run
contract.
