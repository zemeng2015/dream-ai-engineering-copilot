<!-- SPDX-License-Identifier: Apache-2.0 -->

# DemoCorp Java Demo Repo

This is a synthetic Java example used by DREAM tests and demos. It is not a real
DemoCorp production repository.

## Fake Architecture

The repository models a generic long-running job execution workflow:

- `JobExecutionController` exposes API-like operations for starting a job and checking status.
- `JobExecutionService` coordinates validation, async status tracking, batch execution, and result collection.
- `AsyncJobStatusTracker` stores in-memory job status for local demo behavior.
- `BatchJobAdapter` simulates a downstream batch execution boundary.
- `JobResultCollector` simulates output collection after a job completes.
- `JobStatus` defines synthetic status values.

The examples are intentionally simple so DREAM can demonstrate source-backed requirement
analysis without relying on real company code or external systems.
