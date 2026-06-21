# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
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
