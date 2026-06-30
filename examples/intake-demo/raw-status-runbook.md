# Forecast Status Runbook

Operators use this runbook when a long-running forecast execution appears stuck in RUNNING.
The first check is whether the current Task is still progressing or whether StatusTracker failed
to persist a terminal state after the processor completed.

# Review Gate

Knowledge Stewards must review parsed sections before this source enters the demo_team runbook
knowledge pack. The reviewer should confirm that task-level status, stale polling, timeout, and
operator escalation concepts were extracted.

# API Contract Notes

The execution status endpoint should expose job status, task status, terminal state, timestamps,
and a safe user-facing message for stale RUNNING behavior. The UI should not invent timeout values.

# Regression Coverage

Tests should cover queued, running, failed, completed, cancelled, partial success, timeout, and
processor-finished-but-persistence-failed scenarios.
