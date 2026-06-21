# SPDX-License-Identifier: Apache-2.0

from dream.requirement_cases.models import (
    ClarificationQuestion,
    ContextEvidence,
    ImpactItem,
    RequirementCase,
)


def render_engineering_brief(
    *,
    case: RequirementCase,
    evidence: list[ContextEvidence],
    impact_items: list[ImpactItem],
    questions: list[ClarificationQuestion],
) -> str:
    impact_text = _impact_lines(impact_items)
    evidence_text = _evidence_lines(evidence)
    question_text = _question_lines(questions)
    sources = _source_lines(evidence)
    return f"""# Engineering Brief

## 1. Request Summary
{case.raw_request}

## 2. Interpreted Intent
DREAM interprets this as a request to clarify and potentially change DemoCorp job
execution behavior, especially async status visibility and operational diagnosability.

## 3. Current Understanding
This brief is source-backed and still incomplete. Human review is required before
implementation scope, API behavior, persistence, or release commitments are finalized.

## 4. Impact Map
{impact_text}

## 5. Relevant Evidence
{evidence_text}

## 6. Role-specific Clarification Questions
{question_text}

## 7. Proposed Implementation Notes
- Confirm the owning application and component before implementation.
- Prefer explicit job status transitions over implicit string states.
- Keep API and UI behavior aligned with the selected status model.
- Update runbook guidance if failure, retry, or timeout behavior changes.

## 8. Test Strategy
- Add or update unit tests for submitted, running, completed, failed, and missing jobs.
- Cover API-like controller behavior when status tracking is exposed externally.
- Include regression checks for existing job execution behavior.

## 9. Risks and Unknowns
- Persistence requirements are not yet confirmed.
- Frontend polling or refresh behavior is not yet confirmed.
- Operational timeout and retry expectations need BA/TL/OPS review.

## 10. Review Checklist
- Requirement alignment is clear.
- Affected code and tests are identified.
- Status values and transitions are documented.
- Human reviewers have answered open role-specific questions.

## 11. Sources Used
{sources}
"""


def render_engineering_brief_prompt(
    *,
    case: RequirementCase,
    evidence: list[ContextEvidence],
    impact_items: list[ImpactItem],
    questions: list[ClarificationQuestion],
    deterministic_draft: str,
) -> str:
    return f"""Rewrite the deterministic DREAM Engineering Brief into a stronger
source-backed engineering brief.

Hard rules:
- Use only synthetic DemoCorp / DFP / ForecastDemo context from the supplied evidence.
- Do not mention real companies, real Jira, real PRs, real repositories, or real endpoints.
- Preserve uncertainty. Do not imply final approval.
- Include exactly these top-level sections:
  # Engineering Brief
  ## 1. Request Summary
  ## 2. Interpreted Intent
  ## 3. Current Understanding
  ## 4. Impact Map
  ## 5. Relevant Evidence
  ## 6. Role-specific Clarification Questions
  ## 7. Proposed Implementation Notes
  ## 8. Test Strategy
  ## 9. Risks and Unknowns
  ## 10. Review Checklist
  ## 11. Sources Used
- Keep Sources Used as explicit bullet paths from the supplied evidence.
- Make the output concise enough for TL/BA/FE/BE/QA/OPS review.

Raw request:
{case.raw_request}

Impact items:
{_impact_lines(impact_items)}

Evidence:
{_evidence_lines(evidence)}

Questions:
{_question_lines(questions)}

Deterministic draft to improve:
{deterministic_draft}
"""


def render_jira_draft(
    *,
    case: RequirementCase,
    evidence: list[ContextEvidence],
    impact_items: list[ImpactItem],
    questions: list[ClarificationQuestion],
) -> str:
    sources = _source_lines(evidence)
    open_questions = "\n".join(
        f"- [{question.target_role}] {question.question}" for question in questions[:10]
    )
    impact_names = ", ".join(item.name for item in impact_items[:5]) or "TBD"
    return f"""# Jira Story Draft

This is a draft for human review.

## Title
{case.title}

## User Story
As a DemoCorp user or operator, I want long-running job execution status to be visible
so that pending, running, completed, and failed work can be understood without guessing.

## Business Goal
Reduce ambiguity in the DemoCorp job execution workflow and improve cross-role handoff
between BA, TL, frontend, backend, QA, and operations.

## In Scope
- Clarify async job status states and behavior.
- Update affected backend/API/test areas where confirmed.
- Keep implementation aligned with the source-backed impact map.

## Out of Scope
- Production test-generation engine work.
- Real Jira, GitHub, or deployment integration.
- Final approval of scope without human review.

## Acceptance Criteria
- Status tracking behavior is documented for submitted, running, completed, and failed jobs.
- Affected components are reviewed: {impact_names}.
- Unit or service tests cover success, missing job, and failure-oriented scenarios.
- Open questions are reviewed by the appropriate roles before implementation.

## Dev Notes
- Use the Engineering Brief as the source-backed context package.
- Preserve existing job execution behavior unless scope explicitly changes it.
- Keep generated or AI-assisted output subject to human review.

## Test Scenarios
- Start a long-running job and observe the submitted/running status.
- Request status for an unknown job and receive a clear response.
- Simulate downstream batch failure and confirm failure handling expectations.
- Verify existing calculator demo tests remain unaffected.

## Open Questions
{open_questions or "- None generated."}

## Sources Used
{sources}
"""


def render_jira_draft_prompt(
    *,
    case: RequirementCase,
    evidence: list[ContextEvidence],
    impact_items: list[ImpactItem],
    questions: list[ClarificationQuestion],
    deterministic_draft: str,
) -> str:
    return f"""Rewrite the deterministic DREAM Jira Story Draft into a better
Jira-ready story for human review.

Hard rules:
- Use only synthetic DemoCorp / DFP / ForecastDemo context from the supplied evidence.
- Do not mention real companies, real Jira URLs, real PR URLs, real repositories, or real endpoints.
- State that this is a draft for human review.
- Keep uncertainty visible in Open Questions.
- Include exactly these top-level sections:
  # Jira Story Draft
  ## Title
  ## User Story
  ## Business Goal
  ## In Scope
  ## Out of Scope
  ## Acceptance Criteria
  ## Dev Notes
  ## Test Scenarios
  ## Open Questions
  ## Sources Used
- Acceptance Criteria must be concrete and reviewable.
- Sources Used must be explicit bullet paths from supplied evidence.

Raw request:
{case.raw_request}

Impact items:
{_impact_lines(impact_items)}

Evidence:
{_evidence_lines(evidence)}

Questions:
{_question_lines(questions)}

Deterministic draft to improve:
{deterministic_draft}
"""


def _impact_lines(items: list[ImpactItem]) -> str:
    if not items:
        return "- No impact items generated."
    return "\n".join(
        f"- **{item.area_type}**: {item.name} ({item.confidence:.2f}) - {item.description}"
        for item in items
    )


def _evidence_lines(evidence: list[ContextEvidence]) -> str:
    if not evidence:
        return "- No matching evidence was retrieved."
    return "\n".join(
        f"- {item.title} [{item.source_type}] ({item.source_path}) - {item.reason}"
        for item in evidence
    )


def _question_lines(questions: list[ClarificationQuestion]) -> str:
    if not questions:
        return "- No role-specific questions generated."
    return "\n".join(
        f"- **{question.target_role}**: {question.question} Why: {question.why_it_matters}"
        for question in questions
    )


def _source_lines(evidence: list[ContextEvidence]) -> str:
    sources = sorted({item.source_path for item in evidence})
    return "\n".join(f"- {source}" for source in sources) or "- No sources used."
