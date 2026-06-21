# SPDX-License-Identifier: Apache-2.0

from dream.knowledge.models import Chunk
from dream.requirements.models import RequirementDraftRequest


def render_requirement_draft(request: RequirementDraftRequest, chunks: list[Chunk]) -> str:
    source_lines = [
        f"- {chunk.title} ({chunk.source_path})"
        for chunk in chunks
    ] or ["- No matching knowledge sources were retrieved."]
    app_text = request.app or "TBD"
    component_text = request.component or "TBD"
    chunk_titles = ", ".join(chunk.title for chunk in chunks) or "no retrieved sources"
    source_text = "\n".join(source_lines)

    return f"""# Requirement Draft

This is a draft for human review.

## Summary
Draft requirement for: {request.rough_business_request}

## Business Goal
Help DemoCorp stakeholders clarify the desired outcome before engineering implementation.

## In Scope
- Capture the requested behavior for {app_text}.
- Align the draft with retrieved team knowledge: {chunk_titles}.
- Identify test scenarios and operational considerations early.

## Out of Scope
- Final approval of business scope.
- Production implementation details beyond MVP-level guidance.
- Automated deployment or release decisions.

## User Flow
1. A user or system initiates the requested workflow.
2. The affected component processes the request.
3. The system reports status, result, or actionable failure information.
4. Operators and users can inspect outcomes using documented DemoCorp procedures.

## Functional Requirements
- The solution must support the rough request: {request.rough_business_request}
- The system should expose clear state transitions and validation behavior.
- Error cases should be visible to users or operators.

## Non-Functional Requirements
- Behavior should be observable through logs, status, and audit-friendly records.
- Failure handling should follow DemoCorp runbook guidance.
- The implementation should be testable with deterministic unit tests.

## Affected Components
- Application: {app_text}
- Component: {component_text}

## Data Inputs / Outputs
- Inputs: request metadata, job or operation identifiers, and user-provided parameters.
- Outputs: status, result summary, validation errors, and operational diagnostics.

## Acceptance Criteria
- The requested workflow can be exercised end-to-end in a demo environment.
- Success, failure, and pending states are covered by tests.
- Documentation and review notes reference the relevant DemoCorp knowledge sources.

## Test Scenarios
- Happy path validates successful processing.
- Invalid input produces a clear error.
- Long-running or failed execution remains observable.
- Regression tests cover affected business logic.

## Open Questions
- Which DemoCorp application owns the final user experience?
- What status values should be externally visible?
- Are there service-level expectations for long-running operations?

## Sources Used
{source_text}
"""

