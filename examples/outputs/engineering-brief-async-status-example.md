<!-- SPDX-License-Identifier: Apache-2.0 -->

# Engineering Brief

## 1. Request Summary

Analysts want to know which Task is still running when a ForecastDemo Job takes
too long. The request implies task-level execution status, clearer progress in
the Execution Monitor, and operator visibility for stuck RUNNING states.

## 2. Interpreted Intent

This is a draft for human review. DREAM interprets the request as async status
tracking for Job, Execution, and Task state transitions across SERVICE_TASK and
BATCH_TASK execution paths.

## 3. Current Understanding

DFP already models Job, Workflow, Task, and Execution. The status tracking design
expects ExecutionStatus and TaskStatus transitions to be persisted by
StatusTracker.java and surfaced through ExecutionController.java. Prior memory
shows INC-103 where the processor completed but status stayed RUNNING.

## 4. Impact Map

- workflow: define how execution status and task status move through QUEUED,
  RUNNING, FAILED, COMPLETED, CANCELLED, and PARTIAL_SUCCESS.
- frontend: update execution-monitor.component.ts polling behavior, stale status
  display, and task-level status messages.
- backend: update StatusTracker.java, ExecutionService.java, and
  ExecutionController.java to expose task-level status.
- batch: confirm BatchJobAdapter.java reports BATCH_TASK timeout and completion
  events consistently with SERVICE_TASK behavior.
- ops: update status-stuck-running-runbook.md for stale RUNNING detection.
- test: add StatusTrackerTest.java and ExecutionServiceTest.java regressions for
  stuck RUNNING and missing task-level status transitions.

## 5. Relevant Evidence

- status-tracking-design.md describes async tracking and polling.
- execution-model.md defines Execution and task execution state.
- job-lifecycle.md defines the user journey from Job creation to output.
- INC-103-status-stuck-running.md records the stuck RUNNING failure mode.
- DFP-101-add-execution-status-tracking.md introduced status tracking.
- DFP-109-execution-monitor-auto-refresh.md covers UI polling.
- PR-502-add-execution-status-polling.md added monitor polling.
- PR-505-status-tracker-persistence.md changed persistence behavior.
- StatusTracker.java owns status persistence.
- ExecutionService.java coordinates execution state changes.
- ExecutionController.java exposes status APIs.
- BatchJobAdapter.java reports batch task state.
- execution-monitor.component.ts renders status progress.
- StatusTrackerTest.java and ExecutionServiceTest.java are expected test anchors.

## 6. Role-specific Clarification Questions

## BA

- What status labels should users see for Job, Execution, and Task levels?
- Should status be shown at job level, task level, or both?

## TL

- Should SERVICE_TASK and BATCH_TASK share the same status model?
- Should status be persisted or derived from execution events?

## FE

- Should the Execution Monitor poll or subscribe to updates?
- What stale RUNNING threshold should display a warning?

## BE

- What is the authoritative source for task status?
- Which component writes each transition into StatusTracker.java?

## QA

- What are the regression tests for stuck RUNNING state?
- Which status transition matrix must be covered?

## OPS

- What runbook update is needed for stuck execution?
- Which metric or log event should trigger operator investigation?

## 7. Proposed Implementation Notes

- Treat task-level status as source-backed data, not a UI-only derived label.
- Expose task execution status from ExecutionController.java.
- Keep SERVICE_TASK and BATCH_TASK transition semantics aligned unless BA/TL
  explicitly define a difference.
- Preserve uncertainty around polling interval, stale thresholds, and persistence
  ownership until roles answer the open questions.

## 8. Test Strategy

- Add StatusTrackerTest.java coverage for QUEUED to RUNNING to COMPLETED.
- Add ExecutionServiceTest.java coverage for stuck RUNNING when persistence fails.
- Add regression coverage for BATCH_TASK timeout and SERVICE_TASK completion.
- Add UI test coverage or manual QA notes for execution-monitor.component.ts
  polling, stale warning, and error state display.

## 9. Risks and Unknowns

- status stuck RUNNING if StatusTracker.java fails to persist COMPLETED.
- missing task-level status transition for mixed SERVICE_TASK and BATCH_TASK.
- missing UI polling behavior for stale or failed status updates.
- missing regression tests for task-level transition edge cases.

## 10. Review Checklist

- Confirm status labels with BA.
- Confirm persistence ownership with TL/BE.
- Confirm Execution Monitor polling behavior with FE.
- Confirm StatusTrackerTest.java and ExecutionServiceTest.java coverage with QA.
- Confirm status-stuck-running-runbook.md update with OPS.

## 11. Sources Used

- status-tracking-design.md
- execution-model.md
- job-lifecycle.md
- INC-103-status-stuck-running.md
- DFP-101-add-execution-status-tracking.md
- DFP-109-execution-monitor-auto-refresh.md
- PR-502-add-execution-status-polling.md
- PR-505-status-tracker-persistence.md
- StatusTracker.java
- ExecutionService.java
- ExecutionController.java
- BatchJobAdapter.java
- execution-monitor.component.ts
- StatusTrackerTest.java
- ExecutionServiceTest.java
