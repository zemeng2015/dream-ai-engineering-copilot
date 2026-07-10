# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
import sys
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


def _write_fake_gh(fake_bin: Path, runs: list[dict]) -> None:
    fake_bin.mkdir(parents=True, exist_ok=True)
    state_path = fake_bin / "fake-gh-state.json"
    state_path.write_text(json.dumps({"runs": runs}), encoding="utf-8")

    fake_gh = r'''
import json
import sys
from pathlib import Path

state = json.loads(Path(__file__).with_name("fake-gh-state.json").read_text(encoding="utf-8"))
args = sys.argv[1:]

def arg_after(name):
    try:
        return args[args.index(name) + 1]
    except (ValueError, IndexError):
        return ""

if args[:2] == ["run", "list"]:
    print(json.dumps(state["runs"]))
elif args[:2] == ["run", "view"]:
    run_id = args[2]
    for run in state["runs"]:
        if str(run.get("databaseId")) == str(run_id):
            print(json.dumps(run))
            break
    else:
        print(f"run not found: {run_id}", file=sys.stderr)
        sys.exit(1)
elif args[:2] == ["run", "download"]:
    run_id = str(args[2])
    output_dir = Path(arg_after("--dir"))
    output_dir.mkdir(parents=True, exist_ok=True)
    backend_url = f"https://dream-run-{run_id}.example.com"

    (output_dir / f"alibaba-release-20260707-{run_id}.json").write_text(
        json.dumps({"backendUrl": backend_url}),
        encoding="utf-8",
    )
    (output_dir / f"showcase-20260707-{run_id}.json").write_text(
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
    bundle_dir = output_dir / f"final-upload-bundle-20260707-{run_id}-001"
    bundle_dir.mkdir(parents=True, exist_ok=True)
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
    (output_dir / f"final-upload-bundle-20260707-{run_id}-001.zip").write_bytes(
        f"fixture bundle {run_id}".encode("utf-8")
    )
    print(f"downloaded {run_id}")
else:
    print("unsupported fake gh command: " + " ".join(args), file=sys.stderr)
    sys.exit(1)
'''
    if os.name == "nt":
        (fake_bin / "gh.py").write_text(fake_gh, encoding="utf-8")
        (fake_bin / "gh.cmd").write_text(
            f'@echo off\r\n"{sys.executable}" "%~dp0gh.py" %*\r\n',
            encoding="utf-8",
        )
    else:
        gh_path = fake_bin / "gh"
        gh_path.write_text(f"#!{sys.executable}\n{fake_gh}", encoding="utf-8")
        gh_path.chmod(0o755)


def _release_run(run_id: int, status: str, conclusion: str, created_at: str) -> dict:
    return {
        "databaseId": run_id,
        "headSha": f"sha-{run_id}",
        "status": status,
        "conclusion": conclusion,
        "displayTitle": f"Release {run_id}",
        "workflowName": "Qwen Cloud Release",
        "url": f"https://github.com/example/actions/runs/{run_id}",
        "createdAt": created_at,
        "updatedAt": created_at,
    }


def _run_ingest_with_fake_gh(
    tmp_path: Path,
    runs: list[dict],
    *,
    allow_draft: bool = False,
) -> dict:
    fake_bin = tmp_path / "fake-bin"
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()
    _write_fake_gh(fake_bin, runs)

    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-Repo",
        "example/dream",
        "-OutputDir",
        str(output_dir),
    ]
    if allow_draft:
        command.append("-AllowDraft")

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("github-release-artifact-ingest-*.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text(encoding="utf-8-sig"))


def _step(report: dict, name: str) -> dict:
    return next(step for step in report["steps"] if step["name"] == name)


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


def test_github_release_artifact_ingest_selects_latest_completed_success(
    tmp_path,
) -> None:
    report = _run_ingest_with_fake_gh(
        tmp_path,
        [
            _release_run(303, "in_progress", "", "2026-07-07T20:30:00Z"),
            _release_run(302, "completed", "failure", "2026-07-07T20:20:00Z"),
            _release_run(301, "completed", "success", "2026-07-07T20:10:00Z"),
        ],
    )

    assert report["status"] == "READY"
    assert report["runId"] == "301"
    assert "latest completed successful run" in report["releaseRunSelection"]
    assert "activeSkipped=1" in report["releaseRunSelection"]
    assert _step(report, "release_run_success")["ok"] is True
    assert report["backendUrl"] == "https://dream-run-301.example.com"


def test_github_release_artifact_ingest_allow_draft_selects_latest_completed(
    tmp_path,
) -> None:
    report = _run_ingest_with_fake_gh(
        tmp_path,
        [
            _release_run(403, "in_progress", "", "2026-07-07T20:30:00Z"),
            _release_run(402, "completed", "failure", "2026-07-07T20:20:00Z"),
            _release_run(401, "completed", "success", "2026-07-07T20:10:00Z"),
        ],
        allow_draft=True,
    )

    assert report["status"] == "READY"
    assert report["runId"] == "402"
    assert "-AllowDraft is set" in report["releaseRunSelection"]
    assert _step(report, "release_run_success")["ok"] is False
    assert _step(report, "release_run_success")["required"] is False
    assert _step(report, "release_run_draft_artifacts_allowed")["ok"] is True
    assert report["backendUrl"] == "https://dream-run-402.example.com"


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
    assert '[string]$Branch = "codex/champion-memory-loop"' in ingest
    docs = (ROOT / "docs/qwencloud-github-release-workflow.md").read_text(
        encoding="utf-8-sig"
    )
    action_board = (ROOT / "scripts/qwencloud-final-action-board.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_sprint = (ROOT / "scripts/qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )
    external_handoff = (
        ROOT / "scripts/qwencloud-final-external-handoff.ps1"
    ).read_text(encoding="utf-8-sig")
    final_checklist = (ROOT / "docs/qwencloud-final-5min-checklist.md").read_text(
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
    assert "Select-ReleaseRun" in ingest
    assert "releaseRunSelection" in ingest
    assert "selected latest completed successful run" in ingest
    assert "-Required (-not [bool]$AllowDraft)" in ingest
    assert "release_run_draft_artifacts_allowed" in ingest
    assert "release run is not downloadable" in ingest
    assert "allowDraft = [bool]$AllowDraft" in ingest
    assert "-RunId \"<run-id>\" -AllowDraft" in docs
    assert "-RunId \"<workflow-run-id>\" -AllowDraft" in action_board
    assert "-RunId \"<workflow-run-id>\" -AllowDraft" in final_sprint
    assert "-RunId \"<workflow-run-id>\" -AllowDraft" in external_handoff
    assert "-RunId \"<workflow-run-id>\" -AllowDraft" in final_checklist
    assert "qwencloud-release-proof" in action_board
    assert "qwencloud-release-proof" in final_sprint
