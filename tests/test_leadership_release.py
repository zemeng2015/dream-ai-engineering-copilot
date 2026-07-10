# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
from pathlib import Path

import pytest

from dream.core.errors import DreamError
from dream.leadership_demo.release import (
    CRITICAL_SOURCE_PATHS,
    GitReleaseState,
    LeadershipReleaseBuilder,
    LeadershipReleaseManifest,
    LeadershipReleaseVerifier,
)


def test_release_critical_paths_bind_pilot_control_plane() -> None:
    required = {
        "docs/pilot-security-foundation.md",
        "docs/connector-lifecycle-foundation.md",
        "docs/dlp-enforcement-foundation.md",
        "docs/provider-egress-foundation.md",
        "docs/security-decision-evidence-foundation.md",
        "docs/pilot-evidence-export-foundation.md",
        "docs/pilot-evidence-custody-foundation.md",
        "frontend/package-lock.json",
        "dream/api/security.py",
        "dream/config/validator.py",
        "dream/security/identity.py",
        "dream/security/policy.py",
        "dream/security/evidence.py",
        "dream/pilot_evidence/exporter.py",
        "dream/pilot_evidence/custody.py",
    }

    assert required <= set(CRITICAL_SOURCE_PATHS)


def test_release_candidate_hashes_current_source_evidence_and_frontend(tmp_path: Path) -> None:
    project_root = _release_project(tmp_path)
    manifest = LeadershipReleaseBuilder(project_root=project_root).build(
        output_dir=tmp_path / "release"
    )

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

    verification = LeadershipReleaseVerifier(project_root=project_root).verify(
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
    project_root = _release_project(tmp_path)
    release_dir = tmp_path / "release"
    manifest = LeadershipReleaseBuilder(project_root=project_root).build(
        output_dir=release_dir
    )
    tampered = manifest.model_copy(update={"source_snapshot_sha256": "0" * 64})
    manifest_path = release_dir / "tampered.json"
    manifest_path.write_text(tampered.model_dump_json(indent=2), encoding="utf-8")

    loaded = LeadershipReleaseManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    assert loaded.source_snapshot_sha256 == "0" * 64
    verification = LeadershipReleaseVerifier(project_root=project_root).verify(manifest_path)
    assert not verification.passed
    assert "source_snapshot" in verification.failures


def _release_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "project"
    for relative_path in CRITICAL_SOURCE_PATHS:
        path = project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {relative_path}\n", encoding="utf-8")

    preflight_dir = project_root / "artifacts/leadership-preflight"
    benchmark_dir = preflight_dir / "benchmark"
    rehearsal_dir = project_root / "artifacts/leadership-rehearsal"
    frontend_dir = project_root / "frontend/dist/frontend/browser"
    for directory in [preflight_dir, benchmark_dir, rehearsal_dir, frontend_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    _write_json(
        preflight_dir / "leadership-preflight.json",
        {
            "ready_for_demo": True,
            "warnings": [],
            "checks": [{"check_id": "git_hygiene", "status": "pass"}],
        },
    )
    _write_json(
        rehearsal_dir / "leadership-rehearsal.json",
        {
            "passed": True,
            "baseline_restored": True,
            "external_writes_performed": False,
        },
    )
    _write_json(
        benchmark_dir / "leadership-ab-benchmark-suite.json",
        {
            "evidence_tier": "harness_validation",
            "repetitions": 3,
            "same_provider_verified": True,
            "same_model_verified": True,
            "same_request_verified": True,
            "same_contract_verified": True,
        },
    )
    for path in [
        preflight_dir / "leadership-preflight.md",
        rehearsal_dir / "leadership-rehearsal.md",
        benchmark_dir / "leadership-ab-benchmark-suite.md",
    ]:
        path.write_text("fixture evidence\n", encoding="utf-8")
    (frontend_dir / "index.html").write_text("<html></html>\n", encoding="utf-8")

    _git(project_root, "init")
    _git(project_root, "config", "user.email", "leadership-release-test@example.invalid")
    _git(project_root, "config", "user.name", "Leadership Release Test")
    _git(project_root, "add", ".")
    _git(project_root, "commit", "-m", "fixture")
    _git(project_root, "branch", "-M", "codex/leadership-product")
    return project_root


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _git(project_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
