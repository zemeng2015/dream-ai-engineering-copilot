<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Concept Memory: Config Validation"
doc_type: "concept"
team_id: "demo_team"
app: "ForecastDemo"
component: "config-validation"
concepts:
  - config validation
  - concept memory
related_jira:
  - DFP-107
related_pr:
  - PR-506
related_incidents:
  - INC-106
---

    # Concept Memory: Config Validation

    ## What It Means
    Config Validation is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

    ## Related Domain Objects
    TaskDefinition, Job

    ## Related UI Areas
    Task-level upload validation messages

    ## Related Java Backend Classes
    JobController, WorkflowService

    ## Related AWS / Cloud Components
    Service task preflight validation

    ## Related Python Processors
    InputValidator

    ## Related Tests
    test_input_validator.py

    ## Related Incidents
    - INC-106

    ## Related Jira
    - DFP-107

    ## Related PRs
    - PR-506

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
    Always ask whether invalid config blocks Execution creation or fails a Task after start. Link the request to related incidents and historical PRs before drafting scope.

    ## PR Review Hints
    Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
