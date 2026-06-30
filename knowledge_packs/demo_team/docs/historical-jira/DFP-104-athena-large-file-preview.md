<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Use Athena-style query for large file preview"
doc_type: "historical-jira"
team_id: "demo_team"
app: "ForecastDemo"
component: "delivery-history"
concepts:
  - DFP-104
  - use athena-style query for large file preview
related_jira:
  - DFP-104
related_pr:
  - PR-504
related_incidents:
  - INC-107
  - INC-104
---

    # Jira Story

    ## Key
    DFP-104

    ## Title
    Use Athena-style query for large file preview

    ## Background
    Large outputs need query-based preview with partition predicates. This synthetic Jira story lets DREAM retrieve historical delivery patterns for DFP requirement analysis.

    ## User Story
    As a DFP stakeholder, I want use athena-style query for large file preview so that Analysts, Operators, and Admins can handle forecast Executions with less ambiguity.

    ## Functional Requirements
    - Preserve Job, Workflow, Task, and Execution vocabulary.
    - Update affected UI, backend, orchestration, processor, or runbook components as needed.
    - Surface user-safe messages for Analyst and Operator workflows.
    - Record audit-friendly status, retry, output, or configuration decisions.

    ## Acceptance Criteria
    - Relevant happy path and failure path are covered.
    - Impact on Execution status, Task status, output artifacts, or Workflow versioning is documented.
    - Role-specific open questions are resolved before implementation.
    - Regression tests link back to related incidents when present.

    ## Affected Components
    - Execution Monitor or Output Preview Page when UI behavior changes.
    - Java controllers, services, domain models, adapters, and collectors.
    - AWS-style state machine or processor boundary when orchestration changes.
    - Runbooks and PR review checklists.

    ## Dev Notes
    Use synthetic DFP code paths and do not introduce real external endpoints.

    ## Test Scenarios
    - Success path for requested behavior.
    - Failure or timeout path.
    - Operator investigation or retry path when applicable.
    - Regression path for linked incidents.

    ## Open Questions
    - Which role owns final behavior wording?
    - Which statuses should be visible in the UI?
    - Does this require runbook or audit log updates?

    ## Related Incidents
    - INC-107
- INC-104

    ## Related PRs
    - PR-504

    ## Current Status
    Synthetic completed story used for DREAM demo retrieval.
