<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "DFP Glossary"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "domain-model"
concepts:
  - Job
  - Workflow
  - Task
  - Execution
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-101
  - DFP-106
  - DFP-110
related_pr:
  - PR-502
  - PR-509
  - PR-508
related_incidents:
  - INC-103
  - INC-105
  - INC-102
---

# DFP Glossary

## Purpose
Defines the core DemoCorp Forecast Platform vocabulary used across requirements, code reviews, runbooks, Jira history, incidents, and fake code.

## Domain Context
DFP is a synthetic forecast platform where Analysts create Jobs, select versioned Workflows, upload task-level files, execute Workflows, monitor asynchronous Execution status, preview outputs, and download results.

## Key Behaviors
- Job is the analyst-created forecast case with name, owner, workflow, status, createdAt, and updatedAt.
- Workflow is a versioned ordered graph of Tasks with dependencies, execution type, and output expectations.
- Task is SERVICE_TASK or BATCH_TASK.
- Execution is a run instance with status, timestamps, task executions, and output artifacts.

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
- DFP-110

## Related Fake PRs
- PR-502
- PR-509
- PR-508

## Related Fake Incidents
- INC-103
- INC-105
- INC-102

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
