<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Admin workflow console"
doc_type: "historical-pr"
team_id: "demo_team"
app: "ForecastDemo"
component: "delivery-history"
concepts:
  - PR-507
  - admin workflow console
related_code:
  - frontend/src/app/jobs/job-detail.component.ts
  - backend-api/src/main/java/com/democorp/dfp/workflow/WorkflowController.java
related_jira:
  - DFP-105
  - DFP-108
related_pr:
  - PR-507
---

    # Pull Request

    ## PR ID
    PR-507

    ## Title
    Admin workflow console

    ## Summary
    Synthetic DFP pull request documenting a historical implementation pattern. DREAM uses this to reason about PR review risks and likely missing tests.

    ## Files Changed
    - frontend/src/app/jobs/job-detail.component.ts
- backend-api/src/main/java/com/democorp/dfp/workflow/WorkflowController.java

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
    - DFP-105
- DFP-108

    ## Related Incidents
    - None

    ## Related Runbooks
    - status-stuck-running-runbook.md
    - output-collection-failure-runbook.md
    - partial-completion-runbook.md
