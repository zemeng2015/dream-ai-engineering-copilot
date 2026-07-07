# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.llm import LLMResponse
from dream.memory import EngineeringMemoryRetriever
from dream.requirement_cases import (
    RequirementCaseCreateRequest,
    RequirementCaseRepository,
    RequirementCaseService,
)


class FakeLLMProvider:
    provider_name = "fake-openai-compatible"
    model_name = "fake-model"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> LLMResponse:
        self.prompts.append(prompt)
        if "# Jira Story Draft" in prompt:
            text = """# Jira Story Draft

This is a draft for human review.

## Title
Fake LLM Jira Draft

## User Story
As a DemoCorp reviewer, I want a source-backed story.

## Business Goal
Improve review readiness.

## In Scope
- Source-backed scope.

## Out of Scope
- Production implementation approval.

## Acceptance Criteria
- Sources are cited.

## Dev Notes
- Human review required.

## Test Scenarios
- Regression path is identified.

## Open Questions
- Which role owns final approval?

## Sources Used
- fake-source.md
"""
        else:
            text = """# Engineering Brief

## 1. Request Summary
Fake LLM brief.

## 2. Interpreted Intent
Improve review readiness.

## 3. Current Understanding
Human review is required.

## 4. Impact Map
- backend: source-backed change.

## 5. Relevant Evidence
- fake-source.md

## 6. Role-specific Clarification Questions
- BA: What outcome is expected?

## 7. Proposed Implementation Notes
- Keep scope narrow.

## 8. Test Strategy
- Add regression coverage.

## 9. Risks and Unknowns
- Scope still needs approval.

## 10. Review Checklist
- Sources checked.

## 11. Sources Used
- fake-source.md
"""
        return LLMResponse(
            text=text,
            model_name=self.model_name,
            provider_name=self.provider_name,
        )


def _service(
    tmp_path,
    *,
    audit_repository: AuditRepository | None = None,
    llm_provider: FakeLLMProvider | None = None,
) -> RequirementCaseService:
    audit_logger = AuditLogger(
        repository=audit_repository or AuditRepository(tmp_path / "audit.sqlite")
    )
    codebase_repository = CodebaseIndexRepository(tmp_path / "artifacts")
    CodebaseIndexer(repository=codebase_repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )
    memory_retriever = EngineeringMemoryRetriever(
        codebase_repository=codebase_repository,
        codebase_retriever=CodebaseRetriever(repository=codebase_repository),
    )
    return RequirementCaseService(
        repository=RequirementCaseRepository(tmp_path / "cases.sqlite"),
        memory_retriever=memory_retriever,
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
        llm_provider=llm_provider,
    )


def test_create_requirement_case(tmp_path) -> None:
    service = _service(tmp_path)

    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
            created_by_role="BA",
        )
    )

    assert snapshot.case.case_id.startswith("case-")
    assert snapshot.case.status == "created"


def test_analyze_case_retrieves_doc_and_code_evidence(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )

    analyzed = service.analyze_case(snapshot.case.case_id)

    source_types = {item.source_type for item in analyzed.evidence}
    assert "knowledge_doc" in source_types
    assert {"code_file", "code_symbol", "test_file"} & source_types


def test_impact_map_contains_backend_api_and_test_items(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )

    analyzed = service.analyze_case(snapshot.case.case_id)
    area_types = {item.area_type for item in analyzed.impact_items}

    assert {"backend", "api", "test"}.issubset(area_types)


def test_role_specific_questions_for_core_roles(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )
    service.analyze_case(snapshot.case.case_id)

    roles = {question.target_role for question in service.generate_questions(snapshot.case.case_id)}
    tl_questions = service.generate_questions(snapshot.case.case_id, role="TL")

    assert {"BA", "TL", "FE", "BE", "QA"}.issubset(roles)
    assert tl_questions
    assert {question.target_role for question in tl_questions} == {"TL"}


def test_engineering_brief_and_jira_draft_include_sources(tmp_path) -> None:
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
    service = _service(tmp_path, audit_repository=audit_repository)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )
    service.analyze_case(snapshot.case.case_id)

    context = service.prepare_jira_draft_context(snapshot.case.case_id)
    brief = service.generate_engineering_brief(snapshot.case.case_id)
    jira = service.generate_jira_draft(snapshot.case.case_id)
    records = audit_repository.list_audit_records()

    assert "# Jira Story Draft" in context.deterministic_markdown
    assert "Hard rules" in context.prompt
    assert context.prompt_char_count == len(context.prompt)
    assert "# Engineering Brief" in brief.markdown
    assert "## 4. Impact Map" in brief.markdown
    assert "## 11. Sources Used" in brief.markdown
    assert "# Jira Story Draft" in jira.markdown
    assert "## Acceptance Criteria" in jira.markdown
    assert "## Open Questions" in jira.markdown
    assert brief.sources_used
    assert jira.sources_used
    assert any(record.use_case == "jira_draft_context" for record in records)


def test_jira_draft_preserves_output_reconciliation_intent(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request=(
                "Output reconciliation should show collected, skipped, and "
                "retry-needed files after partial completion"
            ),
        )
    )
    service.analyze_case(snapshot.case.case_id)

    jira = service.generate_jira_draft(snapshot.case.case_id)

    assert "output reconciliation" in jira.markdown.lower()
    assert "skipped" in jira.markdown.lower()
    assert "retry" in jira.markdown.lower()
    assert "submitted/running" not in jira.markdown.lower()


def test_question_answers_drive_jira_readiness_and_audit(tmp_path) -> None:
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
    service = _service(tmp_path, audit_repository=audit_repository)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )
    analyzed = service.analyze_case(snapshot.case.case_id)

    early_jira = service.generate_jira_draft(analyzed.case.case_id)
    early_readiness = service.jira_readiness(analyzed.case.case_id)
    assert early_readiness.ready is False
    assert "clarification question" in " ".join(early_jira.warnings)

    for question in analyzed.questions:
        service.answer_question(
            analyzed.case.case_id,
            question.question_id,
            f"Approved answer for {question.target_role}.",
            answered_by="api-test",
        )

    jira = service.generate_jira_draft(analyzed.case.case_id)
    readiness = service.jira_readiness(analyzed.case.case_id)
    snapshot_after_answers = service.get_case(analyzed.case.case_id)
    records = audit_repository.list_audit_records()

    assert readiness.ready is True
    assert readiness.status == "jira_ready_draft"
    assert snapshot_after_answers.case.status == "jira_ready_draft"
    assert "Approved answer for BA." in jira.markdown
    assert all(question.status == "answered" for question in snapshot_after_answers.questions)
    assert any(record.use_case == "requirement_question_answer" for record in records)
    assert any(record.use_case == "jira_readiness_check" for record in records)


def test_question_waiver_drives_readiness_and_audit(tmp_path) -> None:
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
    service = _service(tmp_path, audit_repository=audit_repository)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )
    analyzed = service.analyze_case(snapshot.case.case_id)
    waived_question = analyzed.questions[0]

    waived = service.waive_question(
        analyzed.case.case_id,
        waived_question.question_id,
        "Out of scope for this release: documented as a demo handoff risk.",
        waived_by="api-test",
    )
    for question in analyzed.questions[1:]:
        service.answer_question(
            analyzed.case.case_id,
            question.question_id,
            f"Approved answer for {question.target_role}.",
            answered_by="api-test",
        )

    jira = service.generate_jira_draft(analyzed.case.case_id)
    readiness = service.jira_readiness(analyzed.case.case_id)
    snapshot_after_review = service.get_case(analyzed.case.case_id)
    records = audit_repository.list_audit_records()

    expected_waiver_reason = (
        "Out of scope for this release: documented as a demo handoff risk."
    )
    assert waived.status == "waived"
    assert waived.waived_reason == expected_waiver_reason
    assert readiness.ready is True
    assert readiness.status == "jira_ready_draft"
    assert readiness.open_questions == 0
    assert readiness.waived_questions == 1
    assert any(question.status == "waived" for question in snapshot_after_review.questions)
    assert "Waived: Out of scope for this release" in jira.markdown
    assert "_pending human response_" not in jira.markdown
    assert any(record.use_case == "requirement_question_waive" for record in records)


def test_requirement_case_brief_and_jira_can_use_llm_provider(tmp_path) -> None:
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
    provider = FakeLLMProvider()
    service = _service(tmp_path, audit_repository=audit_repository, llm_provider=provider)
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution",
        )
    )
    service.analyze_case(snapshot.case.case_id)

    brief = service.generate_engineering_brief(snapshot.case.case_id)
    jira = service.generate_jira_draft(snapshot.case.case_id)
    records = audit_repository.list_audit_records()

    assert "# Engineering Brief" in brief.markdown
    assert "# Jira Story Draft" in jira.markdown
    assert len(provider.prompts) == 2
    assert "Hard rules" in provider.prompts[0]
    assert any(
        record.use_case == "engineering_brief"
        and record.model_provider == provider.provider_name
        and record.model_name == provider.model_name
        for record in records
    )
    assert any(
        record.use_case == "jira_draft"
        and record.model_provider == provider.provider_name
        and record.model_name == provider.model_name
        for record in records
    )
