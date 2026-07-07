# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-release-summary.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def _check(summary: dict, name: str) -> dict:
    return next(item for item in summary["checks"] if item["name"] == name)


def test_release_summary_extracts_backend_showcase_and_bundle(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()
    backend_url = "https://dream-memoryagent.example.com"

    (output_dir / "alibaba-release-20260707-120000.json").write_text(
        json.dumps({"backendUrl": backend_url}),
        encoding="utf-8",
    )
    (output_dir / "showcase-20260707-120001.json").write_text(
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
    (output_dir / "deploy-preflight-20260707-120002.json").write_text(
        json.dumps({"checks": [{"name": "docker.smoke_showcase", "ok": True, "required": True}]}),
        encoding="utf-8",
    )
    (output_dir / "final-readiness-20260707-120003.json").write_text(
        json.dumps(
            {
                "readyForFinalSubmit": False,
                "backendUrl": backend_url,
                "checks": [
                    {"name": "backend_url_present", "ok": True, "required": True},
                    {"name": "demo_video_url_present", "ok": False, "required": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "final-action-board-20260707-120004.json").write_text(
        json.dumps({"nextActions": [{"name": "Publish public demo video"}]}),
        encoding="utf-8",
    )
    bundle_dir = output_dir / "final-upload-bundle-20260707-120005-001"
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
    bundle_zip = output_dir / "final-upload-bundle-20260707-120005-001.zip"
    bundle_zip.write_bytes(b"fixture bundle")

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-NoGitHubStepSummary",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summaries = sorted(output_dir.glob("release-summary-*.json"))
    markdown = sorted(output_dir.glob("release-summary-*.md"))
    assert len(summaries) == 1
    assert len(markdown) == 1

    summary = json.loads(summaries[0].read_text(encoding="utf-8-sig"))
    assert summary["status"] == "DRAFT"
    assert summary["backendUrl"] == backend_url
    assert summary["showcase"]["ready"] is True
    assert summary["showcase"]["endpoint"] == "/qwencloud/showcase"
    assert summary["finalBundle"]["missingRequiredItems"] == ["public_demo_video_url"]
    assert len(summary["finalBundle"]["zipSha256"]) == 64
    assert summary["finalBundle"]["releaseSummaryPackagingOk"] is True
    assert summary["finalBundle"]["embeddedReleaseSummaryItems"] == []
    assert _check(summary, "final_bundle_no_embedded_release_summary")["ok"] is True

    markdown_text = markdown[0].read_text(encoding="utf-8-sig")
    assert "Qwen Cloud Release Summary" in markdown_text
    assert "Backend URL" in markdown_text
    assert "/qwencloud/showcase" in markdown_text
    assert "public_demo_video_url" in markdown_text
    assert "generated after bundle" in markdown_text


def test_release_summary_rejects_bundle_with_embedded_stale_summary(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()
    backend_url = "https://dream-memoryagent.example.com"

    (output_dir / "showcase-20260707-130001.json").write_text(
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
    (output_dir / "deploy-preflight-20260707-130002.json").write_text(
        json.dumps({"checks": []}),
        encoding="utf-8",
    )
    (output_dir / "final-readiness-20260707-130003.json").write_text(
        json.dumps(
            {
                "readyForFinalSubmit": True,
                "backendUrl": backend_url,
                "demoVideoUrl": "https://www.youtube.com/watch?v=abc123fixture",
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "final-action-board-20260707-130004.json").write_text(
        json.dumps({"nextActions": []}),
        encoding="utf-8",
    )
    bundle_dir = output_dir / "final-upload-bundle-20260707-130005-001"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "readyForUpload": True,
                "backendUrl": backend_url,
                "demoVideoUrl": "https://www.youtube.com/watch?v=abc123fixture",
                "missingRequiredItems": [],
                "items": [
                    {"name": "github_release_summary_script"},
                    {"name": "latest_github_release_summary_json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "final-upload-bundle-20260707-130005-001.zip").write_bytes(
        b"fixture bundle"
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-NoGitHubStepSummary",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(
        sorted(output_dir.glob("release-summary-*.json"))[0].read_text(
            encoding="utf-8-sig"
        )
    )

    assert summary["status"] == "DRAFT"
    assert summary["readyForFinalSubmit"] is False
    assert summary["finalBundle"]["ready"] is True
    assert summary["finalBundle"]["releaseSummaryPackagingOk"] is False
    assert summary["finalBundle"]["embeddedReleaseSummaryItems"] == [
        "latest_github_release_summary_json"
    ]
    packaging_check = _check(summary, "final_bundle_no_embedded_release_summary")
    assert packaging_check["ok"] is False
    assert "latest_github_release_summary_json" in packaging_check["details"]


def test_release_workflow_and_bundle_register_release_summary() -> None:
    workflow = (ROOT / ".github/workflows/qwencloud-release.yml").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts/qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    finalizer = (ROOT / "scripts/qwencloud-finalize-after-urls.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_sprint = (ROOT / "scripts/qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_readiness = (ROOT / "scripts/qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )
    scorecard = (ROOT / "scripts/qwencloud-judging-scorecard.ps1").read_text(
        encoding="utf-8-sig"
    )
    docs = (ROOT / "docs/qwencloud-github-release-workflow.md").read_text(
        encoding="utf-8-sig"
    )

    assert "Summarize release proof" in workflow
    assert "scripts/qwencloud-release-summary.ps1" in workflow
    assert "$GITHUB_STEP_SUMMARY" not in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "actions: read" in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "Install proof capture tooling" in workflow
    assert "sudo apt-get install -y ffmpeg" in workflow
    assert "ffprobe -version" in workflow
    assert "Chrome or Chromium is required for Alibaba proof screenshot capture." in workflow
    assert (
        "scripts/qwencloud-final-upload-bundle.ps1 @common -SkipGitHubSecrets "
        "-SkipLocalVideoChecks -AllowDraft"
    ) in workflow
    assert "latest_github_release_summary_markdown" not in final_bundle
    assert "latest_github_release_summary_json" not in final_bundle
    assert "github_release_summary_script" in final_bundle
    assert "releaseSummaryPackaging" in final_bundle
    assert "not_bundled_generate_after_zip_hash" in final_bundle
    assert 'Invoke-Step -Name "release-summary"' in finalizer
    assert "releaseSummaryJson" in finalizer
    assert 'Invoke-SprintStep -Name "final-sprint-release-summary"' in final_sprint
    assert "releaseSummaryReady" in final_sprint
    assert "releaseSummaryJson" in final_sprint
    assert "scripts/qwencloud-release-summary.ps1" in final_readiness
    assert "scripts/qwencloud-release-summary.ps1" in scorecard
    assert "workflow run summary" in docs
    assert "generated after the final upload bundle" in docs
    assert "Qwen Cloud Release" in docs
    assert "showcase proof" in docs
    assert "Proof capture tooling setup" in docs
    assert "skips the GitHub secrets audit inside Actions" in docs
    assert "sets `GH_TOKEN` from the GitHub-provided `github.token`" in docs
    assert "`contents: read` and `actions: read`" in docs
