<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Concept Memory: Output Collection"
doc_type: "concept"
team_id: "demo_team"
app: "ForecastDemo"
component: "output-collection"
concepts:
  - output collection
  - concept memory
related_jira:
  - DFP-110
related_pr:
  - PR-503
  - PR-508
related_incidents:
  - INC-102
  - INC-108
---

    # Concept Memory: Output Collection

    ## What It Means
    Output Collection is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

    ## Related Domain Objects
    OutputArtifact, TaskExecution

    ## Related UI Areas
    Output availability and download actions

    ## Related Java Backend Classes
    OutputCollector, StorageAdapter

    ## Related AWS / Cloud Components
    S3-like object storage retry

    ## Related Python Processors
    OutputAggregator

    ## Related Tests
    OutputCollectorTest

    ## Related Incidents
    - INC-102
- INC-108

    ## Related Jira
    - DFP-110

    ## Related PRs
    - PR-503
- PR-508

    ## Common Risks
    - Requirement only mentions one layer while behavior crosses UI, backend, orchestration, processors, and operations.
    - Missing regression test for a known incident.
    - User-facing message does not match backend status semantics.
    - Runbook or audit behavior is not updated.

    ## Common Review Questions
    - Which role owns the expected behavior?
    - What is the terminal state and how is it displayed?
    - What evidence proves the output or status is safe?
    - Which tests prove the failure mode will not repeat?

    ## Requirement Analysis Hints
    Always check idempotency key, retry, checksum, and duplicate artifact handling. Link the request to related incidents and historical PRs before drafting scope.

    ## PR Review Hints
    Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
