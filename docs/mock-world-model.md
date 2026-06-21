<!-- SPDX-License-Identifier: Apache-2.0 -->

# Mock World Model

## Job
A user-created forecast case with name, owner, workflow, status, createdAt, and updatedAt.

## Workflow
A versioned list of Tasks. Published versions are immutable.

## Task
A unit of work. SERVICE_TASK is lightweight. BATCH_TASK is long-running and retryable.

## Execution
A run instance with status, task executions, and output artifacts.

## Output Artifact
Metadata for S3-like output files, preview, checksum, and idempotency key.

## Status Lifecycle
Execution statuses: QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, PARTIAL_SUCCESS. Task statuses: PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, RETRYING.

## Common Incidents
Batch timeout, duplicate output, stuck RUNNING, preview OOM, partial completion undefined, invalid config upload, Athena preview timeout, and output permission denied.

## Cross-role Knowledge Asymmetry
BA, TL, FE, BE, QA, and OPS each own different parts of the same behavior. DREAM connects them through evidence-backed Requirement Cases.
