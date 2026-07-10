<!-- SPDX-License-Identifier: Apache-2.0 -->

# PR Review

The PR review assistant accepts a local unified diff and optional fake Jira-style
context file. It does not connect to GitHub, post comments, approve, reject,
merge, or block a PR.

## Diff Input

The simple parser extracts changed files, added line count, removed line count,
and rough changed content.

## Jira Context

The optional context file is read locally and used only to improve the generated
summary. The demo context is synthetic.

## Review Summary Output

The output includes overall risk, business logic alignment, component impact,
code quality comments, test coverage comments, runtime risk, security/data
concerns, suggested reviewer questions, and sources used.

## Codebase Memory Enhancement

When a `repo_name` is provided and a codebase index exists, PR review also:

- Looks up changed files in codebase memory
- Identifies related files, symbols, concepts, and tests
- Adds a `Related Codebase Memory` section
- Suggests source-to-test coverage checks

If no index exists, DREAM falls back to document and diff context and includes
this warning:

`No codebase index found for this repo/team. Review used document and diff context only.`

## Governed Memory Policy

PR Review also searches the team's latest MemoryClaim scan with the same policy
used by Requirement Case generation:

- only effective `approved` claims can enter the prompt;
- candidate, rejected, and quarantined claims remain outside generation;
- approved claims involved in unresolved single-value conflicts are blocked and
  returned as explicit warnings;
- human-reviewed approved claims are retained ahead of auto-approved code facts
  when the PR prompt has a bounded claim budget; and
- claim id, reviewer, review timestamp, and evidence paths are preserved in the
  review output, `sources_used`, Context Trail, Context Pack, and Audit record.

The API response exposes `memory_claims_used`, `blocked_memory_claim_ids`, and
`context_trail_id`. A missing memory scan does not fail PR Review; it produces a
warning and continues with document, codebase, and graph context.
