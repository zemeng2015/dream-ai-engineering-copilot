---
title: "Execution Model"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "execution-model"
concepts:
  - Execution
  - execution status
  - task status
  - partial success
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-101
  - DFP-106
  - DFP-109
related_pr:
  - PR-505
  - PR-509
related_incidents:
  - INC-103
  - INC-105
---

# Execution Model

## Purpose
Defines Execution and TaskExecution status behavior across UI, backend, orchestration, and processors.

## Domain Context
Execution is a run instance of a Job. TaskExecution records provide task-level progress, retry, failure, skipped, and completion signals.

## Key Behaviors
- Execution statuses are QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, and PARTIAL_SUCCESS.
- Task statuses are PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, and RETRYING.
- PARTIAL_SUCCESS requires explicit optional-task rules.

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
- DFP-101
- DFP-106
- DFP-109

## Related Fake PRs
- PR-505
- PR-509

## Related Fake Incidents
- INC-103
- INC-105

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
