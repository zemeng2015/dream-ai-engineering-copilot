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
    open_questions = "\n".join(_question_status_line(question) for question in questions[:10])
    impact_names = ", ".join(item.name for item in impact_items[:5]) or "TBD"
    affected_files = _affected_file_lines(evidence, impact_items)
    historical_context = _historical_context_lines(evidence)
    story = _jira_story_context(case)
    return f"""# Jira Story Draft

This is a draft for human review.

## Title
{case.title}

## User Story
{story["user_story"]}

## Business Goal
{story["business_goal"]}

## In Scope
{story["in_scope"]}

## Out of Scope
- Production test-generation engine work.
- Real Jira, GitHub, or deployment integration.
- Final approval of scope without human review.

## Acceptance Criteria
{story["acceptance_criteria"]}
- Affected components are reviewed: {impact_names}.
- Affected files are reviewed or explicitly marked out of scope.
- Open questions are reviewed by the appropriate roles before implementation.

## Dev Notes
- Use the Engineering Brief as the source-backed context package.
- Preserve existing job execution behavior unless scope explicitly changes it.
- Keep generated or AI-assisted output subject to human review.
- Affected files:
{affected_files}
- Historical context:
{historical_context}

## Test Scenarios
{story["test_scenarios"]}

## Open Questions
{open_questions or "- None generated."}

## Sources Used
{sources}
"""


def _jira_story_context(case: RequirementCase) -> dict[str, str]:
    request_text = case.raw_request.lower()
    output_terms = ("output", "reconciliation", "skipped", "partial", "retry")
    if any(term in request_text for term in output_terms):
        return {
            "user_story": (
                "As a DemoCorp user or operator, I want output reconciliation to show "
                "collected, skipped, partial, and retry-needed artifacts so that "
                "handoff and recovery decisions are not based on guesswork."
            ),
            "business_goal": (
                "Reduce ambiguity in DemoCorp output collection and recovery workflows, "
                "especially when jobs complete partially or require operator retry."
            ),
            "in_scope": "\n".join(
                [
                    "- Clarify output collection and reconciliation states.",
                    "- Preserve collected/skipped/retry-needed artifact behavior.",
                    "- Update affected backend/API/test areas where confirmed.",
                    "- Keep implementation aligned with the source-backed impact map.",
                ]
            ),
            "acceptance_criteria": "\n".join(
                [
                    "- Output reconciliation documents collected and skipped results.",
                    "- Partial completion behavior is visible to reviewers and operators.",
                    "- Retry guidance is explicit when reconciliation cannot finish cleanly.",
                    "- Unit or service tests cover success, partial, skipped, and retry paths.",
                ]
            ),
            "test_scenarios": "\n".join(
                [
                    "- Complete output collection and verify collected artifacts are listed.",
                    "- Simulate skipped or partial artifacts and verify reconciliation status.",
                    "- Trigger a retry-needed output path and verify operator guidance.",
                    "- Verify existing job execution tests remain unaffected.",
                ]
            ),
        }
    return {
        "user_story": (
            "As a DemoCorp user or operator, I want long-running job execution status "
            "to be visible so that pending, running, completed, and failed work can "
            "be understood without guessing."
        ),
        "business_goal": (
            "Reduce ambiguity in the DemoCorp job execution workflow and improve "
            "cross-role handoff between BA, TL, frontend, backend, QA, and operations."
        ),
        "in_scope": "\n".join(
            [
                "- Clarify async job status states and behavior.",
                "- Update affected backend/API/test areas where confirmed.",
                "- Keep implementation aligned with the source-backed impact map.",
            ]
        ),
        "acceptance_criteria": "\n".join(
            [
                "- Status tracking behavior is documented for submitted jobs.",
                "- Running, completed, and failed states have clear expected behavior.",
                "- Unit or service tests cover success, missing job, and failure scenarios.",
            ]
        ),
        "test_scenarios": "\n".join(
            [
                "- Start a long-running job and observe the submitted/running status.",
                "- Request status for an unknown job and receive a clear response.",
                "- Simulate downstream batch failure and confirm handling expectations.",
                "- Verify existing calculator demo tests remain unaffected.",
            ]
        ),
    }


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
- Preserve the user's specific business intent; do not broaden output reconciliation
  requests into generic status tracking unless the evidence requires it.
- If the raw request mentions output, reconciliation, skipped files, partial files,
  or retry, the Title and User Story must preserve those terms.
- Do not replace collected/skipped/retry-needed output behavior with only generic
  submitted/running/completed/failed status language.
- Name concrete affected files when evidence or impact items include code, API, test,
  UI, or runbook paths.
- Include an impact summary with counts for affected files, memory documents,
  open questions, and test references inside existing sections.
- Acceptance Criteria must be concrete, reviewable, and tied to the retrieved evidence.
- Dev Notes must call out likely implementation files, historical Jira/PR/incident
  references, and missing tests when available.
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
        f"- {item.title} [{item.source_type}] ({item.source_path}) "
        f"Evidence: {_compact_excerpt(item.excerpt)} Why selected: {item.reason}"
        for item in evidence
    )


def _compact_excerpt(value: str, limit: int = 400) -> str:
    compact = " ".join(value.split())
    return compact[:limit] if compact else "_No excerpt available._"


def _question_lines(questions: list[ClarificationQuestion]) -> str:
    if not questions:
        return "- No role-specific questions generated."
    return "\n".join(
        f"- **{question.target_role}**: {question.question} "
        f"Status: {question.status}. {_answer_line(question)} "
        f"Why: {question.why_it_matters}"
        for question in questions
    )


def _affected_file_lines(
    evidence: list[ContextEvidence],
    impact_items: list[ImpactItem],
) -> str:
    paths: list[str] = []
    for item in impact_items:
        paths.extend(source for source in item.sources if _looks_like_file_path(source))
    paths.extend(item.source_path for item in evidence if _looks_like_file_path(item.source_path))
    unique_paths = sorted(dict.fromkeys(paths))
    if not unique_paths:
        return "  - No concrete file paths were identified."
    return "\n".join(f"  - {path}" for path in unique_paths[:12])


def _historical_context_lines(evidence: list[ContextEvidence]) -> str:
    historical = [
        item
        for item in evidence
        if item.source_type in {"incident", "historical_jira", "historical_pr"}
        or "/incidents/" in item.source_path
        or "/historical-jira/" in item.source_path
        or "/historical-pr/" in item.source_path
    ]
    if not historical:
        return "  - No historical Jira, PR, or incident references were retrieved."
    return "\n".join(
        f"  - {item.title}: {item.source_path} ({item.reason})" for item in historical[:8]
    )


def _looks_like_file_path(value: str) -> bool:
    return "." in value.rsplit("/", maxsplit=1)[-1]


def _question_status_line(question: ClarificationQuestion) -> str:
    return (
        f"- [{question.target_role}] {question.question} "
        f"Status: {question.status}. {_answer_line(question)}"
    )


def _answer_line(question: ClarificationQuestion) -> str:
    if question.status == "waived":
        reason = question.waived_reason or "No waiver reason supplied."
        return f"Waived: {reason}"
    if question.answer:
        return f"Answer: {question.answer}"
    return "Answer: _pending human response_."


def _source_lines(evidence: list[ContextEvidence]) -> str:
    sources = sorted({item.source_path for item in evidence})
    return "\n".join(f"- {source}" for source in sources) or "- No sources used."
