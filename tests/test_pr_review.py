# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.context.repository import ContextArtifactRepository
from dream.memory import MemoryClaimRetriever, MemoryDistillationService
from dream.memory.repository import MemoryDistillationRepository
from dream.review import PRReviewAssistant, PRReviewRequest
from dream.review.diff_parser import parse_unified_diff


def test_diff_parser_extracts_summary() -> None:
    summary = parse_unified_diff(
        """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1 +1,2 @@
-old
+new
+extra
"""
    )

    assert summary.files_changed == ["A.java"]
    assert summary.added_line_count == 2
    assert summary.removed_line_count == 1
    assert "extra" in summary.rough_changed_content


def test_pr_review_summary_generation_with_mock_provider(tmp_path) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    assistant = PRReviewAssistant(audit_logger=audit_logger)

    response = assistant.review(
        PRReviewRequest(
            team_id="demo_team",
            pr_diff_path="examples/fake_pr_diff.diff",
            jira_context_path="examples/fake_jira_ticket.md",
        )
    )

    assert response.run_id.startswith("pr-")
    assert "# AI PR Review Summary" in response.markdown
    assert "Human review is required." in response.markdown
    assert response.sources_used
    assert audit_logger.repository.get_audit_record(response.run_id) is not None


def test_pr_review_uses_codebase_memory_when_index_exists(tmp_path) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    codebase_repository = CodebaseIndexRepository(tmp_path / "artifacts")
    CodebaseIndexer(repository=codebase_repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )
    assistant = PRReviewAssistant(
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
        codebase_retriever=CodebaseRetriever(repository=codebase_repository),
    )

    response = assistant.review(
        PRReviewRequest(
            team_id="demo_team",
            repo_name="java-demo-repo",
            pr_diff_path="examples/fake_pr_diff.diff",
            jira_context_path="examples/fake_jira_ticket.md",
        )
    )

    assert "## Related Codebase Memory" in response.markdown
    assert "JobExecutionService.java" in response.markdown
    assert "JobExecutionServiceTest.java" in response.markdown
    assert not any("No codebase index found" in warning for warning in response.warnings)


def test_pr_review_falls_back_when_codebase_index_missing(tmp_path) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    assistant = PRReviewAssistant(
        audit_logger=audit_logger,
        codebase_repository=CodebaseIndexRepository(tmp_path / "artifacts"),
    )

    response = assistant.review(
        PRReviewRequest(
            team_id="demo_team",
            repo_name="missing-repo",
            pr_diff_path="examples/fake_pr_diff.diff",
            jira_context_path="examples/fake_jira_ticket.md",
        )
    )

    assert "No codebase index found for this repo/team" in response.markdown
    assert any("No codebase index found" in warning for warning in response.warnings)


def test_pr_review_uses_only_policy_approved_claims_in_prompt_context_and_audit(
    tmp_path,
) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    artifacts = tmp_path / "artifacts"
    codebase_repository = CodebaseIndexRepository(artifacts)
    memory_repository = MemoryDistillationRepository(artifacts)
    memory_service = MemoryDistillationService(
        repository=memory_repository,
        codebase_repository=codebase_repository,
        audit_logger=audit_logger,
    )
    scan = memory_service.scan(
        team_id="demo_team",
        repo_path="examples/dfp-demo-repo",
        repo_name="dfp-demo-repo",
    )
    claim = next(
        item
        for item in scan.claims
        if item.entity.canonical_name == "execution status"
        and item.relation.type == "documented_by"
        and any(
            span.path.endswith("docs/architecture/status-tracking-design.md")
            for span in item.evidence.spans
        )
    )
    assistant = PRReviewAssistant(
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
        codebase_retriever=CodebaseRetriever(repository=codebase_repository),
        memory_repository=memory_repository,
        memory_claim_retriever=MemoryClaimRetriever(repository=memory_repository),
    )
    changed_path = (
        "backend-api/src/main/java/com/democorp/dfp/execution/ExecutionController.java"
    )
    request = PRReviewRequest(
        team_id="demo_team",
        repo_name="dfp-demo-repo",
        pr_diff_text="\n".join(
            [
                f"diff --git a/{changed_path} b/{changed_path}",
                f"--- a/{changed_path}",
                f"+++ b/{changed_path}",
                "@@ -1 +1,2 @@",
                "-return execution;",
                "+return execution.withTaskStatus();",
                "+// expose which forecast task is still running",
            ]
        ),
        jira_context_text=(
            "Show task-level execution status and refresh the Forecast Execution page."
        ),
    )

    candidate_response = assistant.review(request)
    assert claim.claim_id not in candidate_response.memory_claims_used
    assert f"memory-claim:{claim.claim_id}" not in candidate_response.sources_used

    memory_service.review_claim(
        team_id="demo_team",
        claim_id=claim.claim_id,
        new_status="approved",
        reviewer="Leadership Reviewer",
        reason="Synthetic architecture source is approved for the bounded PR review.",
        scan_id=scan.scan_id,
    )
    approved_response = assistant.review(request)
    assert claim.claim_id in approved_response.memory_claims_used
    assert f"`{claim.claim_id}`" in approved_response.markdown
    assert f"memory-claim:{claim.claim_id}" in approved_response.sources_used
    assert any(
        path.endswith("docs/architecture/status-tracking-design.md")
        for path in approved_response.sources_used
    )

    audit = audit_logger.repository.get_audit_record(approved_response.run_id)
    assert audit is not None
    assert f"memory-claim:{claim.claim_id}" in audit.retrieved_source_paths
    trail = ContextArtifactRepository().load_trail(approved_response.context_trail_id)
    used_claim = next(
        item for item in trail.memory_claims_used if item.claim_id == claim.claim_id
    )
    assert used_claim.status == "approved"
    assert used_claim.reviewed_by == "Leadership Reviewer"
    pack = ContextArtifactRepository().load_context_pack(
        f"context-pack-{approved_response.run_id}"
    )
    assert [item.claim_id for item in pack.selected_memory_claims] == (
        approved_response.memory_claims_used
    )

    memory_service.review_claim(
        team_id="demo_team",
        claim_id=claim.claim_id,
        new_status="rejected",
        reviewer="Leadership Reviewer",
        reason="Verify rejected claims are removed from future PR review context.",
        scan_id=scan.scan_id,
    )
    rejected_response = assistant.review(request)
    assert claim.claim_id not in rejected_response.memory_claims_used
    assert f"memory-claim:{claim.claim_id}" not in rejected_response.sources_used
