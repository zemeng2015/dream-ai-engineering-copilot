# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository
from dream.context import ContextEvaluationService, ContextIntelligenceService
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRepository
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.requirement_cases.repository import RequirementCaseRepository
from dream.review import PRReviewAssistant, PRReviewRequest


def test_context_trace_pack_prompt_and_retrieval_eval(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "dream.sqlite"))
    codebase_repository = CodebaseIndexRepository()
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    CodebaseIndexer(repository=codebase_repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/dfp-demo-repo",
        repo_name="dfp-demo-repo",
    )
    graph_repository = EvidenceGraphRepository()
    EvidenceGraphBuilder(
        repository=graph_repository,
        codebase_repository=codebase_repository,
        audit_logger=audit_logger,
    ).build(team_id="demo_team", repo_name="dfp-demo-repo")
    service = RequirementCaseService(
        repository=RequirementCaseRepository(tmp_path / "cases.sqlite"),
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
    )
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request=(
                "Users want to know which task is still running when a forecast job "
                "takes too long"
            ),
            created_by_role="BA",
        )
    )
    analyzed = service.analyze_case(snapshot.case.case_id)
    context_service = ContextIntelligenceService(
        requirement_repository=service.repository,
        graph_repository=graph_repository,
        codebase_repository=codebase_repository,
    )

    trail = context_service.trace_case(analyzed.case.case_id)
    pack = context_service.assemble_case(analyzed.case.case_id)
    preview = context_service.prompt_for_case(analyzed.case.case_id, target="jira_draft")
    result = ContextEvaluationService(context_service=context_service).evaluate_case(
        case_id=analyzed.case.case_id,
        profile_id="async-status-tracking",
    )

    assert trail.json_path
    assert trail.selected_evidence
    assert pack.selected_evidence_count > 0
    assert "Jira Story Draft" in preview.prompt_text
    assert result.scorecard.target_type == "retrieval_context"
    assert (tmp_path / "artifacts" / "context-trails" / trail.trail_id / "trail.json").exists()
    assert (
        tmp_path / "artifacts" / "context-packs" / pack.context_pack_id / "context-pack.md"
    ).exists()


def test_pr_review_writes_context_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "dream.sqlite"))
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))

    response = PRReviewAssistant(audit_logger=audit_logger).review(
        PRReviewRequest(
            team_id="demo_team",
            pr_diff_path="examples/fake_pr_diff.diff",
            jira_context_path="examples/fake_jira_ticket.md",
            repo_name=None,
        )
    )

    assert response.run_id
    assert (
        tmp_path
        / "artifacts"
        / "context-trails"
        / f"context-trail-{response.run_id}"
        / "trail.json"
    ).exists()
    assert (
        tmp_path
        / "artifacts"
        / "prompt-previews"
        / f"prompt-preview-{response.run_id}-pr_review"
        / "prompt-preview.md"
    ).exists()
