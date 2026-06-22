<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Concept Memory: Execution Status"
doc_type: "concept"
team_id: "demo_team"
app: "ForecastDemo"
component: "execution-status"
concepts:
  - execution status
  - concept memory
related_jira:
  - DFP-101
  - DFP-109
  - DFP-112
related_pr:
  - PR-502
  - PR-505
  - PR-510
related_incidents:
  - INC-103
  - INC-105
---

    # Concept Memory: Execution Status

    ## What It Means
    Execution Status is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

    ## Related Domain Objects
    Execution, TaskExecution

    ## Related UI Areas
    Execution Monitor

    ## Related Java Backend Classes
    StatusTracker, ExecutionService, ExecutionController

    ## Related AWS / Cloud Components
    Step Functions events and stale status metrics

    ## Related Python Processors
    ForecastProcessor completion callback

    ## Related Tests
    StatusTrackerTest and status-transition-test-plan.md

    ## Related Incidents
    - INC-103
- INC-105

    ## Related Jira
    - DFP-101
- DFP-109
- DFP-112

    ## Related PRs
    - PR-502
- PR-505
- PR-510

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
    Always ask which statuses are user-visible, stale, retryable, and terminal. Link the request to related incidents and historical PRs before drafting scope.

    ## PR Review Hints
    Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
