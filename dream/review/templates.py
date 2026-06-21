# SPDX-License-Identifier: Apache-2.0

from dream.codebase.models import CodebaseSearchResult, TestMapping
from dream.knowledge.models import Chunk
from dream.review.diff_parser import DiffSummary


def render_pr_review_summary(
    *,
    diff_summary: DiffSummary,
    jira_context: str | None,
    chunks: list[Chunk],
    codebase_results: list[CodebaseSearchResult] | None = None,
    related_tests: list[TestMapping] | None = None,
    warnings: list[str] | None = None,
) -> str:
    total_changed = diff_summary.added_line_count + diff_summary.removed_line_count
    if total_changed > 120 or len(diff_summary.files_changed) > 8:
        risk = "High"
    elif total_changed > 40 or len(diff_summary.files_changed) > 3:
        risk = "Medium"
    else:
        risk = "Low"

    files = "\n".join(f"- {path}" for path in diff_summary.files_changed) or "- No files parsed."
    codebase_results = codebase_results or []
    related_tests = related_tests or []
    sources = _source_lines(chunks, codebase_results, related_tests)
    codebase_lines = _codebase_lines(codebase_results)
    test_lines = _test_lines(related_tests)
    warning_lines = _warning_lines(warnings or [])
    jira_note = "Jira context was provided." if jira_context else "No Jira context was provided."

    return f"""# AI PR Review Summary

This is an AI-generated review aid. It does not approve, reject, merge, or block the PR.
Human review is required.

## Overall Risk
{risk}

## Changed Files
{files}

## Related Codebase Memory
{codebase_lines}

## Business Logic Alignment
{jira_note} Review the changed behavior against the stated requirement and DemoCorp domain workflow.

## Component Impact
Assess whether the changed files affect service coordination, API status behavior, tests, or runbook
expectations identified in the codebase memory.

## Code Quality Comments
- Added lines: {diff_summary.added_line_count}
- Removed lines: {diff_summary.removed_line_count}
- Check naming, error handling, and small-method readability in the affected code.

## Test Coverage Comments
- Confirm unit tests cover success and failure paths.
- Add regression tests for async status transitions or job state changes if applicable.
Related tests from codebase memory:
{test_lines}

## Runtime / Operational Risk
- Verify long-running operations remain observable.
- Ensure failure handling aligns with the DemoCorp runbook and emits clear diagnostics.

## Security / Data Concerns
- Confirm no sensitive DemoCorp data is introduced in logs, errors, or examples.
- Validate inputs before they affect persistent state.

## Suggested Reviewer Questions
- Does this change preserve existing behavior for current users?
- Are pending, completed, and failed states represented clearly?
- What operational signal helps support teams diagnose failures?

## Warnings
{warning_lines}

## Sources Used
{sources}
"""


def _codebase_lines(results: list[CodebaseSearchResult]) -> str:
    if not results:
        return "- No related codebase memory was available."
    lines = []
    for result in results:
        line = f"- {result.title} [{result.result_type}] ({result.source_path}) - {result.reason}"
        if result.result_type.startswith("graph_") and result.excerpt:
            line += f" Evidence path: {result.excerpt}"
        lines.append(line)
    return "\n".join(lines)


def _test_lines(mappings: list[TestMapping]) -> str:
    if not mappings:
        return (
            "- No source-to-test mapping was found; reviewers should check missing tests "
            "manually."
        )
    return "\n".join(
        f"- {mapping.source_file} -> {mapping.test_file} ({mapping.confidence:.2f})"
        for mapping in mappings
    )


def _warning_lines(warnings: list[str]) -> str:
    return "\n".join(f"- {warning}" for warning in warnings) or "- None."


def _source_lines(
    chunks: list[Chunk],
    codebase_results: list[CodebaseSearchResult],
    related_tests: list[TestMapping],
) -> str:
    lines = [f"- {chunk.title} ({chunk.source_path})" for chunk in chunks]
    lines.extend(
        f"- {result.title} ({result.source_path})"
        for result in codebase_results
        if result.result_type != "concept"
    )
    lines.extend(f"- Related test: {mapping.test_file}" for mapping in related_tests)
    deduped = list(dict.fromkeys(lines))
    return "\n".join(deduped) or "- No matching sources were retrieved."
