# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-live-inputs-intake.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_live_inputs_intake_reports_missing_external_inputs(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-EnvFile",
        str(env_file),
        "-SkipExternalUrlChecks",
        "-SkipBackendChecks",
        "-AllowDraft",
    ]

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("live-inputs-intake-*.json"))
    markdown_reports = sorted(output_dir.glob("live-inputs-intake-*.md"))
    assert len(reports) == 1
    assert len(markdown_reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    checks = {item["name"]: item for item in report["checks"]}

    assert report["status"] == "DRAFT"
    assert report["readyForLiveInputs"] is False
    assert checks["env_file_present"]["ok"] is False
    assert checks["demo_video_url_present"]["ok"] is False
    assert checks["backend_url_present"]["ok"] is False
    assert checks["alibaba_screenshot_exists"]["ok"] is False
    assert checks["alibaba_proof_video_exists"]["ok"] is False
    assert "env_file_present" in report["missingRequiredChecks"]


def test_live_inputs_intake_registered_in_final_submission_flow() -> None:
    script_path = "scripts/qwencloud-live-inputs-intake.ps1"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-final-action-board.ps1",
        "scripts/qwencloud-final-sprint.ps1",
        "scripts/qwencloud-finalize-after-urls.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")

    final_readiness = (ROOT / "scripts" / "qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    assert "live_inputs_intake_ready" in final_readiness
    assert "live_inputs_intake_ready" in final_bundle
    assert "live_inputs_intake_markdown" in final_bundle
    assert "live_inputs_intake_json" in final_bundle

    final_action_board = (
        ROOT / "scripts" / "qwencloud-final-action-board.ps1"
    ).read_text(encoding="utf-8-sig")
    final_sprint = (ROOT / "scripts" / "qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )
    finalize_after_urls = (
        ROOT / "scripts" / "qwencloud-finalize-after-urls.ps1"
    ).read_text(encoding="utf-8-sig")
    assert "live-inputs-intake" in final_action_board
    assert "liveInputsReady" in final_action_board
    assert "Collect live submission inputs" in final_action_board
    assert "final-sprint-live-inputs-intake" in final_sprint
    assert "liveInputsReady" in final_sprint
    assert "Collect live submission inputs" in final_sprint
    assert "live-inputs-intake" in finalize_after_urls
    assert "liveInputsJson" in finalize_after_urls
