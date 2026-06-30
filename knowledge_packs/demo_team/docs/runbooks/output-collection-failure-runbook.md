<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Output Collection Failure Runbook"
doc_type: "runbook"
team_id: "demo_team"
app: "ForecastDemo"
component: "operations"
concepts:
  - operator
  - runbook
  - output collection failure runbook
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
  - INC-102
  - INC-108
---

# Output Collection Failure Runbook

## Purpose
Guides Operators through this synthetic DFP scenario: Execution completed but output artifacts are missing or duplicated.

## Domain Context
Operators connect UI symptoms, backend status, orchestration events, processor output, and storage artifact metadata.

## Key Behaviors
- Check OutputCollector idempotency key, StorageAdapter permissions, checksum, and retry history.
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
- INC-102
- INC-108

## Open Questions Or Review Notes
OPS should decide whether remediation requires a product change or only runbook clarification.
