# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-github-release-artifact-ingest.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_github_release_artifact_ingest_accepts_fixture_source(tmp_path) -> None:
    source_dir = tmp_path / "release-artifact"
    output_dir = tmp_path / "qwencloud-proof"
    source_dir.mkdir()
    output_dir.mkdir()
    backend_url = "https://dream-memoryagent.example.com"

    (source_dir / "alibaba-release-20260707-120000.json").write_text(
        json.dumps({"backendUrl": backend_url}),
        encoding="utf-8",
    )
    (source_dir / "showcase-20260707-120001.json").write_text(
        json.dumps(
            {
                "track": "Track 1: MemoryAgent",
                "runtime": {
                    "status": "ok",
                    "llm_provider": "qwen-cloud",
                    "live_backend_ready": True,
                },
                "scorecard": {
                    "weighted_static_evidence_ready": 100,
                    "weighted_total": 100,
                },
            }
        ),
        encoding="utf-8",
    )
    bundle_dir = source_dir / "final-upload-bundle-20260707-120002-001"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "readyForUpload": False,
                "backendUrl": backend_url,
                "missingRequiredItems": ["public_demo_video_url"],
            }
        ),
        encoding="utf-8",
    )
    (source_dir / "final-upload-bundle-20260707-120002-001.zip").write_bytes(
        b"fixture bundle"
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-ArtifactSourceDir",
            str(source_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("github-release-artifact-ingest-*.json"))
    summaries = sorted(output_dir.glob("release-summary-*.json"))
    assert len(reports) == 1
    assert len(summaries) == 1
    assert (output_dir / "alibaba-release-20260707-120000.json").exists()
    assert (output_dir / "final-upload-bundle-20260707-120002-001.zip").exists()

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    assert report["status"] == "READY"
    assert report["readyForGitHubReleaseArtifactIngest"] is True
    assert report["usingFixture"] is True
    assert report["backendUrl"] == backend_url
    assert report["copiedFileCount"] >= 4
    assert report["releaseSummaryJson"]

    summary = json.loads(summaries[0].read_text(encoding="utf-8-sig"))
    assert summary["backendUrl"] == backend_url
    assert summary["showcase"]["ready"] is True
    assert summary["finalBundle"]["zipSha256"]


def test_github_release_artifact_ingest_registered_in_final_flow() -> None:
    script_path = "scripts/qwencloud-github-release-artifact-ingest.ps1"

    for path in [
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-final-sprint.ps1",
        "scripts/qwencloud-final-action-board.ps1",
        "scripts/qwencloud-final-external-handoff.ps1",
        "scripts/qwencloud-judging-scorecard.ps1",
        "docs/qwencloud-github-release-workflow.md",
        "docs/qwencloud-final-5min-checklist.md",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")

    final_sprint = (ROOT / "scripts/qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts/qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    ingest = (ROOT / script_path).read_text(encoding="utf-8-sig")
    docs = (ROOT / "docs/qwencloud-github-release-workflow.md").read_text(
        encoding="utf-8-sig"
    )

    assert "githubReleaseArtifactIngestReady" in final_sprint
    assert "githubReleaseArtifactIngestJson" in final_sprint
    assert "latest_github_release_artifact_ingest_markdown" in final_bundle
    assert "latest_github_release_artifact_ingest_json" in final_bundle
    assert (
        '$releaseRunSuccess = $run.status -eq "completed" '
        '-and $run.conclusion -eq "success"'
    ) in ingest
    assert (
        '$downloadAllowed = $run.status -eq "completed" -and '
        '($run.conclusion -eq "success" -or [bool]$AllowDraft)'
    ) not in ingest
    assert (
        '$downloadAllowed = $run.status -eq "completed" -and '
        '($releaseRunSuccess -or [bool]$AllowDraft)'
    ) in ingest
    assert (
        'Add-Step -Name "release_run_success" -Ok $releaseRunSuccess'
        in ingest
    )
    assert "release_run_artifact_downloadable" in ingest
    assert "-Required (-not [bool]$AllowDraft)" in ingest
    assert "release_run_draft_artifacts_allowed" in ingest
    assert "release run is not downloadable" in ingest
    assert "allowDraft = [bool]$AllowDraft" in ingest
    assert "-RunId \"<run-id>\" -AllowDraft" in docs
