# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-post-submit-verification.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def _check(report: dict, name: str) -> dict:
    return next(item for item in report["checks"] if item["name"] == name)


def test_post_submit_verification_selects_latest_head_ci_run(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    bundle_dir = output_dir / "final-upload-bundle-fixture"
    bundle_dir.mkdir(parents=True)
    bundle_zip = output_dir / "final-upload-bundle-fixture.zip"
    bundle_zip.write_bytes(b"fixture zip")
    head = "abc123fixture"

    manifest = bundle_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "readyForUpload": True,
                "gitCommit": head,
                "gitWorktreeClean": True,
                "gitRemoteSynced": True,
                "zipPath": str(bundle_zip),
                "items": [
                    {"name": "devpost_packet_markdown"},
                    {"name": "devpost_handoff_html"},
                    {"name": "official_rules_gate_json"},
                    {"name": "local_demo_video_for_public_upload"},
                    {"name": "alibaba_deployment_screenshot"},
                    {"name": "alibaba_backend_proof_recording"},
                ],
            }
        ),
        encoding="utf-8",
    )

    runs_json = tmp_path / "runs.json"
    runs_json.write_text(
        json.dumps(
            [
                {
                    "databaseId": 9001,
                    "headSha": head,
                    "status": "completed",
                    "conclusion": "failure",
                    "displayTitle": "Older failing CI",
                    "url": "https://github.com/example/actions/runs/9001",
                    "createdAt": "2026-07-07T20:00:00Z",
                    "updatedAt": "2026-07-07T20:01:00Z",
                },
                {
                    "databaseId": 9003,
                    "headSha": "other-head",
                    "status": "completed",
                    "conclusion": "success",
                    "displayTitle": "Other head CI",
                    "url": "https://github.com/example/actions/runs/9003",
                    "createdAt": "2026-07-07T20:30:00Z",
                    "updatedAt": "2026-07-07T20:31:00Z",
                },
                {
                    "databaseId": 9002,
                    "headSha": head,
                    "status": "completed",
                    "conclusion": "success",
                    "displayTitle": "Latest passing CI",
                    "url": "https://github.com/example/actions/runs/9002",
                    "createdAt": "2026-07-07T20:20:00Z",
                    "updatedAt": "2026-07-07T20:21:00Z",
                },
            ]
        ),
        encoding="utf-8",
    )
    repo_json = tmp_path / "repo.json"
    repo_json.write_text(
        json.dumps(
            {
                "nameWithOwner": "zemeng2015/dream-ai-engineering-copilot",
                "visibility": "public",
                "private": False,
                "license": {"spdx_id": "Apache-2.0"},
            }
        ),
        encoding="utf-8",
    )
    devpost_html = tmp_path / "devpost.html"
    devpost_html.write_text(
        """
        <html>
          <head><title>DREAM</title></head>
          <body>
            <h1>DREAM</h1>
            <p>Qwen Cloud MemoryAgent submission.</p>
            <a href="https://github.com/zemeng2015/dream-ai-engineering-copilot">Code</a>
            <iframe src="https://www.youtube.com/embed/abc123fixture"></iframe>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-FinalBundleManifest",
            str(manifest),
            "-RunsJsonPath",
            str(runs_json),
            "-RepoJsonPath",
            str(repo_json),
            "-DevpostHtmlPath",
            str(devpost_html),
            "-DevpostProjectUrl",
            "https://devpost.com/software/dream-qwen-cloud-memoryagent",
            "-DemoVideoUrl",
            "https://www.youtube.com/watch?v=abc123fixture",
            "-SkipExternalUrlChecks",
            "-AllowDraft",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("devpost-post-submit-verification-*.json"))
    assert len(reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    latest_ci = _check(report, "latest_head_ci_success")
    bundle_commit = _check(report, "final_bundle_git_commit_matches_head")

    assert latest_ci["ok"] is True
    assert "run=9002" in latest_ci["details"]
    assert "Latest passing CI" in latest_ci["details"]
    assert bundle_commit["ok"] is True
    assert report["repoName"] == "zemeng2015/dream-ai-engineering-copilot"
    assert report["repoRef"] == "codex/champion-memory-loop"
    assert _check(report, "repo_url_github")["ok"] is True
    assert _check(report, "repo_github_public")["ok"] is True
    assert _check(report, "repo_license_apache_2_0")["ok"] is True
    assert _check(report, "devpost_public_project_mentions_repo")["ok"] is True
    assert _check(report, "devpost_public_project_mentions_demo_video")["ok"] is True
    assert _check(report, "devpost_public_project_mentions_track_memoryagent")["required"] is False


def test_post_submit_verification_has_fixtureable_ci_selection() -> None:
    text = SCRIPT.read_text(encoding="utf-8-sig")

    assert "[string]$RunsJsonPath" in text
    assert "[string]$RepoJsonPath" in text
    assert "[string]$DevpostHtmlPath" in text
    assert "[string]$GitHead" in text
    assert "function Get-RepoName" in text
    assert "function Get-DevpostProjectResponse" in text
    assert "function Test-DevpostVideoMention" in text
    assert "function Get-GitHubRepoMetadata" in text
    assert "ConvertTo-FlatArray" in text
    assert "matchingRuns" in text
    assert "gh run list --repo $repoName" in text
    assert '[string]$RepoRef = "codex/champion-memory-loop"' in text
    assert "--branch $RepoRef" in text
    assert "$manifest.gitCommit" in text
    assert "repo_github_public" in text
    assert "repo_license_apache_2_0" in text
    assert "devpost_public_project_mentions_repo" in text
    assert "devpost_public_project_mentions_demo_video" in text


def test_post_submit_verification_only_requires_explicit_bundle() -> None:
    text = SCRIPT.read_text(encoding="utf-8-sig")

    assert "$bundleRequired = -not [string]::IsNullOrWhiteSpace($FinalBundleManifest)" in text
    assert "not requested; pass -FinalBundleManifest for strict bundle verification" in text
    assert "-Required $bundleRequired" in text
