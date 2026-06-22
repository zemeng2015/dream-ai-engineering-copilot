<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Task Model"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "task-model"
concepts:
  - Task
  - SERVICE_TASK
  - BATCH_TASK
  - task config validation
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-102
  - DFP-107
  - DFP-111
related_pr:
  - PR-501
  - PR-506
related_incidents:
  - INC-101
  - INC-106
---

# Task Model

## Purpose
Describes task definitions, SERVICE_TASK and BATCH_TASK behavior, and task-level config.

## Domain Context
SERVICE_TASK entries run lightweight functions. BATCH_TASK entries run longer batch-style processing and require timeout, retry, and Operator visibility.

## Key Behaviors
- TaskDefinition declares task id, display name, type, dependencies, timeout, retry policy, required inputs, and required config fields.
- SERVICE_TASK should fail fast with user-safe errors.
- BATCH_TASK should expose retry and timeout status.

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
- DFP-102
- DFP-107
- DFP-111

## Related Fake PRs
- PR-501
- PR-506

## Related Fake Incidents
- INC-101
- INC-106

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
