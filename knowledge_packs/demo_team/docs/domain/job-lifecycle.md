<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Job Execution Lifecycle"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "job-lifecycle"
concepts:
  - job execution
  - execution status
  - analyst workflow
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-101
  - DFP-109
  - DFP-112
related_pr:
  - PR-502
  - PR-510
related_incidents:
  - INC-103
  - INC-105
---

# Job Execution Lifecycle

## Purpose
Explains the analyst path from Job creation to output download.

## Domain Context
A Job starts as a forecast case, binds to a Workflow version, receives task-level config and input files, creates an Execution, and collects output artifacts.

## Key Behaviors
- Only one active RUNNING Execution is allowed per Job in the demo rules.
- Execution starts QUEUED and moves through RUNNING to a terminal status.
- Job Detail should show latest Execution and output readiness.

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
- DFP-109
- DFP-112

## Related Fake PRs
- PR-502
- PR-510

## Related Fake Incidents
- INC-103
- INC-105

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
