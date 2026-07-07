---
title: Output Reconciliation Intake Demo
app: ForecastDemo
component: knowledge-intake
doc_type: runbooks
concepts: [operator, execution status, runbook, democorp, execution, apache-2, app, component]
source: examples/intake-samples/runbook-output-reconciliation.md
review_status: promoted
---

# Output Reconciliation Intake Demo

Imported through DREAM Knowledge Intake. Human review is required before using
this as authoritative context.

## Overview

<!-- SPDX-License-Identifier: Apache-2.0 -->

---
app: ForecastDemo
component: output-reconciliation
doc_type: runbook
source_system: local_upload
owner: DemoCorp Platform Operations
synthetic: true
---

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-1`

## Scope

This synthetic runbook covers DemoCorp Forecast Platform output reconciliation
for ForecastDemo jobs. It applies when a forecast job finishes orchestration but
the result materialization status is delayed, duplicated, or partially complete.

The runbook is intended for DREAM intake demonstrations only. It does not
describe a real production system.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-2`

## Operating Signals

- Execution status is `PARTIAL_COMPLETE`, `FAILED`, or `COMPLETED_WITH_WARNINGS`.
- Output reconciliation status is `PENDING_RETRY`, `RETRY_REQUESTED`, or
  `RECONCILED`.
- The operator console shows a stable run id and workflow version.
- The latest output manifest has a checksum but the result store row is missing
  or marked stale.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-3`

## Pre-Checks

Before requesting retry:

1. Confirm the execution status is not `RUNNING`.
2. Confirm the run id and workflow version are stable for at least one polling
   interval.
3. Check whether an output reconciliation retry was already requested.
4. Confirm the output manifest checksum matches the expected DemoCorp forecast
   batch id.
5. Capture the operator note in the audit field.

If execution status is still `RUNNING`, retry must be blocked and the operator
should see a message explaining that reconciliation can start only after the
execution state is stable.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-4`

## Standard Recovery

Use standard recovery when the output manifest exists and there is no active
retry request.

1. Mark the output reconciliation record as `RETRY_REQUESTED`.
2. Send one idempotent retry request for the run id.
3. Keep the operator console in read-only mode until the retry completes.
4. Refresh reconciliation status after each polling interval.
5. Move the status to `RECONCILED` only after the result store row and manifest
   checksum agree.

Repeated retry requests for the same run id should return the existing retry
record instead of creating duplicate work.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-5`

## Escalation

Escalate to DemoCorp Platform Operations when:

- the same run id has more than one retry request
- checksum validation fails
- reconciliation stays in `RETRY_REQUESTED` for more than three polling intervals
- the operator note says the source data was manually corrected

Escalation notes should include run id, workflow version, previous status,
current status, checksum state, and operator note.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-6`

## Candidate Knowledge Draft Hints

The intake pipeline should propose these reviewable claims:

- Output reconciliation retry must be blocked while execution status is
  `RUNNING`.
- Retry requests for the same run id should be idempotent.
- Operator-facing retry guidance should mention stable run id, workflow version,
  and checksum state.
- Audit notes should capture the human reason for retry.

Source reference: `artifacts/intake/uploads/intake-5d2fff8695d5.md#section-7`
