# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-deadline-guard.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def _run_deadline_guard(tmp_path: Path, now_utc: str, allow_draft: bool = False):
    output_dir = tmp_path / "qwencloud-proof"
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-NowUtc",
        now_utc,
    ]
    if allow_draft:
        command.append("-AllowDraft")

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    reports = sorted(output_dir.glob("deadline-guard-*.json"))
    report = json.loads(reports[-1].read_text(encoding="utf-8-sig")) if reports else {}
    return result, report


def test_deadline_guard_is_ready_before_submission_deadline(tmp_path) -> None:
    result, report = _run_deadline_guard(tmp_path, "2026-07-08T20:00:00Z")

    assert result.returncode == 0, result.stdout + result.stderr
    checks = {item["name"]: item for item in report["checks"]}

    assert report["status"] == "READY"
    assert report["readyForSubmissionWindow"] is True
    assert report["urgency"] == "open"
    assert report["hoursRemaining"] == 25
    assert checks["submission_window_open"]["ok"] is True
    assert checks["official_snapshot_deadline_present"]["ok"] is True


def test_deadline_guard_reports_draft_after_submission_deadline(tmp_path) -> None:
    result, report = _run_deadline_guard(
        tmp_path,
        "2026-07-09T21:00:01Z",
        allow_draft=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    checks = {item["name"]: item for item in report["checks"]}

    assert report["status"] == "DRAFT"
    assert report["readyForSubmissionWindow"] is False
    assert report["urgency"] == "expired"
    assert checks["submission_window_open"]["ok"] is False


def test_deadline_guard_registered_in_final_submission_flow() -> None:
    script_path = "scripts/qwencloud-deadline-guard.ps1"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")

    final_readiness = (ROOT / "scripts" / "qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    assert "submission_deadline_guard_ready" in final_readiness
    assert "submission_deadline_guard_ready" in final_bundle
    assert "deadline_guard_markdown" in final_bundle
    assert "deadline_guard_json" in final_bundle
