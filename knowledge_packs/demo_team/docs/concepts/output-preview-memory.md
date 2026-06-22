<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Concept Memory: Output Preview"
doc_type: "concept"
team_id: "demo_team"
app: "ForecastDemo"
component: "output-preview"
concepts:
  - output preview
  - concept memory
related_jira:
  - DFP-103
  - DFP-104
related_pr:
  - PR-504
related_incidents:
  - INC-104
  - INC-107
  - INC-108
---

    # Concept Memory: Output Preview

    ## What It Means
    Output Preview is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

    ## Related Domain Objects
    OutputArtifact, Execution

    ## Related UI Areas
    Output Preview Page

    ## Related Java Backend Classes
    OutputPreviewService, AthenaPreviewAdapter

    ## Related AWS / Cloud Components
    Athena-like query and S3-like storage

    ## Related Python Processors
    OutputAggregator manifest metadata

    ## Related Tests
    output-preview-test-plan.md

    ## Related Incidents
    - INC-104
- INC-107
- INC-108

    ## Related Jira
    - DFP-103
- DFP-104

    ## Related PRs
    - PR-504

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
    Always ask size threshold, pagination, partition predicate, and permission behavior. Link the request to related incidents and historical PRs before drafting scope.

    ## PR Review Hints
    Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
