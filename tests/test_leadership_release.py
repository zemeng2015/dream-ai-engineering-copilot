# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from dream.core.errors import DreamError
from dream.leadership_demo.release import (
    GitReleaseState,
    LeadershipReleaseBuilder,
    LeadershipReleaseManifest,
    LeadershipReleaseVerifier,
)


def test_release_candidate_hashes_current_source_evidence_and_frontend(tmp_path: Path) -> None:
    manifest = LeadershipReleaseBuilder().build(output_dir=tmp_path / "release")

    assert manifest.status == "candidate_uncommitted"
    assert manifest.preflight_ready
    assert manifest.rehearsal_passed
    assert manifest.rehearsal_baseline_restored
    assert not manifest.rehearsal_external_writes_performed
    assert manifest.benchmark_repetitions >= 3
    assert manifest.source_file_count > 0
    assert manifest.critical_source_checksums
    assert manifest.evidence_artifact_checksums
    assert manifest.frontend_bundle_file_count > 0

    verification = LeadershipReleaseVerifier().verify(
        tmp_path / "release/leadership-release-manifest.json"
    )
    assert verification.passed


def test_strict_release_rejects_dirty_or_competition_git_state(tmp_path: Path) -> None:
    dirty = GitReleaseState(
        branch="codex/leadership-product",
        commit_sha="a" * 40,
        status_lines=[" M README.md"],
    )
    with pytest.raises(DreamError, match="clean working tree"):
        LeadershipReleaseBuilder(git_state=dirty).build(
            output_dir=tmp_path / "release",
            strict=True,
        )

    competition = dirty.model_copy(
        update={"branch": "codex/champion-memory-loop", "status_lines": []}
    )
    with pytest.raises(DreamError, match="competition branch"):
        LeadershipReleaseBuilder(git_state=competition).build(
            output_dir=tmp_path / "release",
        )


def test_release_verifier_detects_manifest_tampering(tmp_path: Path) -> None:
    release_dir = tmp_path / "release"
    manifest = LeadershipReleaseBuilder().build(output_dir=release_dir)
    tampered = manifest.model_copy(update={"source_snapshot_sha256": "0" * 64})
    manifest_path = release_dir / "tampered.json"
    manifest_path.write_text(tampered.model_dump_json(indent=2), encoding="utf-8")

    loaded = LeadershipReleaseManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    assert loaded.source_snapshot_sha256 == "0" * 64
    verification = LeadershipReleaseVerifier().verify(manifest_path)
    assert not verification.passed
    assert "source_snapshot" in verification.failures
