---
title: "Status Stuck RUNNING Runbook"
doc_type: "runbook"
team_id: "demo_team"
app: "ForecastDemo"
component: "operations"
concepts:
  - operator
  - runbook
  - status stuck running runbook
related_code:
  - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
  - backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
  - frontend/src/app/execution/execution-monitor.component.ts
related_jira:
  - DFP-101
  - DFP-111
  - DFP-112
related_pr:
  - PR-505
  - PR-510
related_incidents:
  - INC-103
---

# Status Stuck RUNNING Runbook

## Purpose
Guides Operators through this synthetic DFP scenario: Execution or TaskExecution remains RUNNING after processor completion.

## Domain Context
Operators connect UI symptoms, backend status, orchestration events, processor output, and storage artifact metadata.

## Key Behaviors
- Compare StatusTracker lastUpdated, orchestration terminal event, processor manifest, and UI polling timestamp.
- Capture execution id, job id, workflow version, task id, task type, and last status update.
- Use retry only when status and idempotency rules are clear.

## Affected Components
- Execution Monitor
- StatusTracker
- OutputCollector
- AWS-style orchestration
- Operator runbooks

## Failure Modes
- Stale status
- Retry without idempotency
- Missing partition predicate
- Unsafe user error

## Test Considerations
- Add regression coverage for linked incident.
- Assert Operator-facing message and audit trail.

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
- DFP-111
- DFP-112

## Related Fake PRs
- PR-505
- PR-510

## Related Fake Incidents
- INC-103

## Open Questions Or Review Notes
OPS should decide whether remediation requires a product change or only runbook clarification.
