---
title: "Data Artifact Model"
doc_type: "domain"
team_id: "demo_team"
app: "ForecastDemo"
component: "output-artifacts"
concepts:
  - output artifacts
  - object storage
  - preview
  - download
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-103
  - DFP-104
  - DFP-110
related_pr:
  - PR-503
  - PR-504
  - PR-508
related_incidents:
  - INC-102
  - INC-104
  - INC-107
  - INC-108
---

# Data Artifact Model

## Purpose
Defines output artifact metadata for forecast results.

## Domain Context
Output artifacts reference S3-like object storage and can be previewed directly or through Athena-like query preview.

## Key Behaviors
- OutputArtifact includes execution id, task id, artifact key, content type, row count, size, checksum, preview mode, and idempotency key.
- OutputCollector writes metadata after task completion and final execution completion.
- OutputPreviewService chooses direct preview or Athena-style preview.

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
- DFP-103
- DFP-104
- DFP-110

## Related Fake PRs
- PR-503
- PR-504
- PR-508

## Related Fake Incidents
- INC-102
- INC-104
- INC-107
- INC-108

## Open Questions Or Review Notes
Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.
