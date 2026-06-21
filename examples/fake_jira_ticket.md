<!-- SPDX-License-Identifier: Apache-2.0 -->

# Add async status tracking for long-running job execution

DemoCorp users of BatchJobDemo need a way to start a long-running job and check
its status later. The current demo flow returns only a final result, which makes
the caller wait for completion.

## Desired Outcome

- Return a stable job id when the job starts.
- Allow callers to read submitted, running, completed, or failed status.
- Keep failure messages safe for display.
- Add unit tests for status transitions and invalid job ids.

