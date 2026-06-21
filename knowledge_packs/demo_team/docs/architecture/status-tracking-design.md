---
title: "Status Tracking Design"
doc_type: "architecture"
team_id: "demo_team"
app: "ForecastDemo"
component: "execution-status"
concepts:
  - execution status
  - task status
  - async tracking
  - polling
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
  - PR-505
  - PR-510
related_incidents:
  - INC-103
  - INC-105
---

# Status Tracking Design

## Purpose
Defines async Execution and Task status tracking across DFP.

## Domain Context
Analysts need to know which Task is still running; Operators need history for stuck executions; FE needs polling; BE needs legal transitions.

## Key Behaviors
- Trace business behavior across UI, Java backend, AWS-style orchestration, and Python processors.
- Preserve DFP vocabulary in API contracts and UI messages.
- Update runbooks, tests, and audit behavior when execution semantics change.

## Affected Components
- frontend/src/app/execution/execution-monitor.component.ts
- backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
- aws/step-functions/job-execution-state-machine.asl.json
- python-processors/processors/input_validator.py

## Failure Modes
- UI polling without backend stale detection.
- Backend status changes without runbook updates.
- Output collection without idempotency.
- Processor validation without user-facing errors.

## Test Considerations
- Add service tests for backend decisions.
- Add UI state tests for status and preview behavior.
- Add processor tests for validation and output metadata.

## Related Docs
- execution-model.md
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
- PR-505
- PR-510

## Related Fake Incidents
- INC-103
- INC-105

## Open Questions Or Review Notes
TL review should check which layers change and which layers only need test or documentation updates.
