---
title: "Concept Memory: Partial Recovery"
doc_type: "concept"
team_id: "demo_team"
app: "ForecastDemo"
component: "partial-recovery"
concepts:
  - partial recovery
  - concept memory
related_jira:
  - DFP-106
related_pr:
  - PR-509
related_incidents:
  - INC-105
---

    # Concept Memory: Partial Recovery

    ## What It Means
    Partial Recovery is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

    ## Related Domain Objects
    Execution, Workflow, Task

    ## Related UI Areas
    PARTIAL_SUCCESS banner and partial output display

    ## Related Java Backend Classes
    ExecutionService, StatusTracker

    ## Related AWS / Cloud Components
    Optional task failure branch

    ## Related Python Processors
    OutputAggregator partial manifest

    ## Related Tests
    partial-completion-test-plan.md

    ## Related Incidents
    - INC-105

    ## Related Jira
    - DFP-106

    ## Related PRs
    - PR-509

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
    Always ask which tasks are critical and whether partial outputs may be previewed or downloaded. Link the request to related incidents and historical PRs before drafting scope.

    ## PR Review Hints
    Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
