# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import (
    CodebaseIndexer,
    CodebaseIndexRepository,
    CodebaseRetriever,
    CodebaseScanner,
)
from dream.review import PRReviewAssistant, PRReviewRequest


def test_dfp_codebase_scanner_finds_multi_layer_repo() -> None:
    files = CodebaseScanner().scan("examples/dfp-demo-repo")
    paths = {file_node.path for file_node in files}

    assert "frontend/src/app/execution/execution-monitor.component.ts" in paths
    assert "backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java" in paths
    assert "python-processors/processors/input_validator.py" in paths
    assert "aws/step-functions/job-execution-state-machine.asl.json" in paths


def test_dfp_codebase_search_returns_status_tracker(tmp_path) -> None:
    repository = CodebaseIndexRepository(tmp_path / "artifacts")
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    CodebaseIndexer(repository=repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/dfp-demo-repo",
        repo_name="dfp-demo-repo",
    )

    results = CodebaseRetriever(repository=repository).search(
        team_id="demo_team",
        repo_name="dfp-demo-repo",
        query="status tracker",
        top_k=10,
    )

    assert any("StatusTracker.java" in result.source_path for result in results)


def test_pr_review_can_use_dfp_fake_diff(tmp_path) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    repository = CodebaseIndexRepository(tmp_path / "artifacts")
    CodebaseIndexer(repository=repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/dfp-demo-repo",
        repo_name="dfp-demo-repo",
    )
    assistant = PRReviewAssistant(
        audit_logger=audit_logger,
        codebase_repository=repository,
        codebase_retriever=CodebaseRetriever(repository=repository),
    )

    response = assistant.review(
        PRReviewRequest(
            team_id="demo_team",
            repo_name="dfp-demo-repo",
            pr_diff_path="examples/pr-diffs/DFP-110-output-collector-idempotency.diff",
            jira_context_path=(
                "knowledge_packs/demo_team/docs/historical-jira/"
                "DFP-110-output-collection-idempotency.md"
            ),
        )
    )

    assert "## Related Codebase Memory" in response.markdown
    assert "OutputCollector" in response.markdown
