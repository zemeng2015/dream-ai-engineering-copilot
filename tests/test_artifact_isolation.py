# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.core.errors import PathTraversalError
from dream.extensions import LocalArtifactStore
from dream.testgen import MockTestGenProvider, TestGenRequest


def test_local_artifact_store_writes_under_configured_root(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    path = store.write_text("reports/demo.md", "# Demo\n")

    assert path == (tmp_path / "artifacts" / "reports" / "demo.md").resolve()
    assert path.read_text(encoding="utf-8") == "# Demo\n"


def test_local_artifact_store_prevents_path_traversal(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    with pytest.raises(PathTraversalError):
        store.write_text("../leak.md", "nope")


def test_generated_artifact_uses_custom_artifact_root(tmp_path, monkeypatch) -> None:
    artifact_root = tmp_path / "custom-artifacts"
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "audit.sqlite"))

    result = MockTestGenProvider().run(
        TestGenRequest(team_id="demo_team", repo_path="examples/java-demo-repo", dry_run=True)
    )

    assert (artifact_root / f"testgen-report-{result.run_id}.md").exists()
