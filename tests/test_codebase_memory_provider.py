# SPDX-License-Identifier: Apache-2.0

from dream.extensions import NativeCodebaseMemoryProvider


def test_native_codebase_memory_provider_readiness(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "dream.sqlite"))
    provider = NativeCodebaseMemoryProvider()

    index = provider.index_repository(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )
    results = provider.search("demo_team", "java-demo-repo", "job status", top_k=5)
    explanation = provider.explain_file(
        "demo_team",
        "java-demo-repo",
        "src/main/java/com/democorp/demo/JobExecutionService.java",
    )
    relationships = provider.export_relationships("demo_team", "java-demo-repo")

    assert index.files
    assert results
    assert explanation["found"] is True
    assert relationships["files"]
