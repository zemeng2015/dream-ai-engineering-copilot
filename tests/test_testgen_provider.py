# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.core.paths import PROJECT_ROOT
from dream.testgen import JTestGenAdapter, MockTestGenProvider, TestGenRequest


def _repo_snapshot(repo_path: Path) -> set[str]:
    return {
        path.relative_to(repo_path).as_posix()
        for path in repo_path.rglob("*")
        if path.is_file()
    }


def test_mock_testgen_provider_does_not_modify_repo(tmp_path) -> None:
    repo_path = PROJECT_ROOT / "examples" / "java-demo-repo"
    before = _repo_snapshot(repo_path)
    provider = MockTestGenProvider(
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    )

    result = provider.run(
        TestGenRequest(team_id="demo_team", repo_path="examples/java-demo-repo", dry_run=True)
    )

    after = _repo_snapshot(repo_path)
    assert before == after
    assert result.status == "dry_run"
    assert result.generated_files
    assert "Human review required: true" in result.report_markdown


def test_jtestgen_adapter_dry_run_safe_behavior() -> None:
    result = JTestGenAdapter().run(
        TestGenRequest(team_id="demo_team", repo_path="examples/java-demo-repo", dry_run=True)
    )

    assert result.status == "dry_run"
    assert result.generated_files == []
    assert "no files were modified" in result.warnings[0].lower()
    assert result.artifact_path is not None

