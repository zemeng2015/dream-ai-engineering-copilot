---
title: "Task config validation"
doc_type: "historical-pr"
team_id: "demo_team"
app: "ForecastDemo"
component: "delivery-history"
concepts:
  - PR-506
  - task config validation
related_code:
  - backend-api/src/main/java/com/democorp/dfp/workflow/TaskDefinition.java
  - python-processors/processors/input_validator.py
related_jira:
  - DFP-107
related_pr:
  - PR-506
related_incidents:
  - INC-106
---

    # Pull Request

    ## PR ID
    PR-506

    ## Title
    Task config validation

    ## Summary
    Synthetic DFP pull request documenting a historical implementation pattern. DREAM uses this to reason about PR review risks and likely missing tests.

    ## Files Changed
    - backend-api/src/main/java/com/democorp/dfp/workflow/TaskDefinition.java
- python-processors/processors/input_validator.py

    ## Important Design Decisions
    - Kept changes scoped to DFP demo components.
    - Preserved Job, Workflow, Task, and Execution vocabulary.
    - Used deterministic behavior and human-reviewable status/output decisions.
    - Avoided real external integrations.

    ## Reviewer Comments
    - Please confirm BATCH_TASK timeout behavior is visible to Operator.
- This PR updates backend status but does not update Execution Monitor error state.
- Missing regression test for duplicate output retry.
- Need to update runbook for stuck RUNNING state.

    ## Test Coverage
    Unit tests were expected for status transitions, output idempotency, preview pagination, retry decisions, or config validation depending on scope.

    ## Risks
    - Cross-layer UI/backend drift.
    - Missing Operator runbook update.
    - Ambiguous status or partial output behavior.
    - Insufficient regression coverage for linked incidents.

    ## Follow-up Items
    - Update related docs and runbooks.
    - Add explicit regression tests.
    - Confirm role-specific open questions are resolved.

    ## Related Jira
    - DFP-107

    ## Related Incidents
    - INC-106

    ## Related Runbooks
    - status-stuck-running-runbook.md
    - output-collection-failure-runbook.md
    - partial-completion-runbook.md
