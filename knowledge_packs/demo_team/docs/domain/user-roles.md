---
title: "DFP User Roles"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "roles"
concepts:
  - Analyst
  - Operator
  - Admin
  - role-specific questions
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-109
  - DFP-111
related_pr:
  - PR-502
  - PR-510
related_incidents:
  - INC-103
  - INC-108
---

# DFP User Roles

## Purpose
Captures business and engineering roles used by Requirement Case analysis.

## Domain Context
DFP features create knowledge asymmetry across Analyst, Operator, Admin, BA, TL, FE, BE, QA, and OPS.

## Key Behaviors
- Analyst creates Jobs, uploads task inputs, executes Jobs, monitors status, previews outputs, and downloads results.
- Operator investigates failed, stuck, or partially complete Executions.
- Admin manages Workflow versions and Task definitions.

## Affected Components
- Job List Page
- Job Detail Page
- Execution Monitor
- Java backend domain models
- AWS-style orchestration
- Python processors

## Failure Modes
- Status values drift between UI and backend.
- Retry behavior produces duplicate outputs.
- Invalid config fails late at execution time.
- Partial completion behavior is not defined.

## Test Considerations
- Cover status transition matrix.
- Cover SERVICE_TASK and BATCH_TASK routing.
- Cover idempotent output collection.
- Cover linked fake incidents as regressions.

## Related Docs
- status-tracking-design.md
- output-collection-design.md

## Related Fake Code Files
- backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
- backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
- frontend/src/app/execution/execution-monitor.component.ts

## Related Fake Jira
- DFP-109
- DFP-111

## Related Fake PRs
- PR-502
- PR-510

## Related Fake Incidents
- INC-103
- INC-108

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
