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

    markdown_text = markdown[0].read_text(encoding="utf-8-sig")
    assert "Qwen Cloud Release Summary" in markdown_text
    assert "Backend URL" in markdown_text
    assert "/qwencloud/showcase" in markdown_text
    assert "public_demo_video_url" in markdown_text


def test_release_workflow_and_bundle_register_release_summary() -> None:
    workflow = (ROOT / ".github/workflows/qwencloud-release.yml").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts/qwencloud-final-upload-bundle.ps1").read_text(
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
    assert "latest_github_release_summary_markdown" in final_bundle
    assert "latest_github_release_summary_json" in final_bundle
    assert "github_release_summary_script" in final_bundle
    assert "scripts/qwencloud-release-summary.ps1" in final_readiness
    assert "scripts/qwencloud-release-summary.ps1" in scorecard
    assert "workflow run summary" in docs
    assert "Qwen Cloud Release" in docs
    assert "showcase proof" in docs
