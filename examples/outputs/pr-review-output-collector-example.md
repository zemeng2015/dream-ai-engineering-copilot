<!-- SPDX-License-Identifier: Apache-2.0 -->

# AI PR Review Summary

This is an AI-generated review aid. It does not approve, reject, merge, or block
the PR. Human review is required.

## Overall Risk

Medium. The change addresses output collection idempotency, but retry behavior
has direct impact on duplicate output prevention and operator investigation.

## Changed Files

- backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java
- backend-api/src/main/java/com/democorp/dfp/output/OutputArtifact.java
- backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java

## Related Codebase Memory

- OutputCollector.java owns output artifact collection and storage retry.
- OutputArtifact.java should carry or derive the idempotency key.
- StorageAdapter.java is the likely boundary for transient storage errors.
- OutputCollectorTest.java should include duplicate retry regression coverage.
- output-collection-memory.md links DFP-110, PR-503, PR-508, and INC-102.

## Business Logic Alignment

DFP-110 asks for output collection idempotency so Analysts do not see duplicate
result files after retry. The PR should make duplicate output impossible for the
same Execution and Task output artifact.

## Component Impact

- backend: OutputCollector.java retry path and idempotency key handling.
- data: OutputArtifact.java identity fields.
- ops: output-collection-failure-runbook.md should explain duplicate detection.
- test: OutputCollectorTest.java should validate retry after transient failure.

## Test Coverage Comments

The PR should include a regression for INC-102 duplicate output. The key missing
test is a storage failure followed by retry that writes exactly one artifact for
the same idempotency key.

## Runtime / Operational Risk

- duplicate output if the idempotency key is missing or unstable.
- retry loop can hide storage permission errors if warnings are swallowed.
- operators need clear audit/log evidence when output collection is skipped as a
  duplicate.

## Suggested Reviewer Questions

- Is the idempotency key stable across retries for the same Execution and Task?
- Does StorageAdapter.java distinguish duplicate write from permission denied?
- Does OutputCollectorTest.java cover transient failure followed by retry?
- Does the runbook mention duplicate output and retry behavior?

## Sources Used

- output-collection-design.md
- output-collection-memory.md
- output-collection-failure-runbook.md
- INC-102-duplicate-output.md
- DFP-110-output-collection-idempotency.md
- PR-503-output-collector-retry-logic.md
- PR-508-output-collection-idempotency.md
- OutputCollector.java
- OutputArtifact.java
- StorageAdapter.java
- OutputCollectorTest.java
