# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-judge-rehearsal.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_qwencloud_judge_rehearsal_generates_lightweight_report(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-SkipRuntimeProof",
        "-SkipFrontendBuild",
        "-SkipReadiness",
        "-AllowDraft",
    ]

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    reports = sorted(output_dir.glob("judge-rehearsal-*.json"))
    markdown_reports = sorted(output_dir.glob("judge-rehearsal-*.md"))
    assert len(reports) == 1
    assert len(markdown_reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    shots = {shot["name"]: shot for shot in report["demoShots"]}
    steps = {step["name"]: step for step in report["steps"]}

    assert report["status"] == "DRAFT"
    assert report["readyForJudgeRehearsal"] is False
    assert Path(report["seedSummaryJson"]).exists()
    assert Path(report["seedZip"]).exists()
    assert Path(report["judgingScorecardJson"]).exists()
    assert shots["Seeded Memory Hub claim review"]["ready"] is True
    assert shots["Audit, eval, and judging alignment"]["ready"] is True
    assert steps["seeded-demo-artifact"]["ok"] is True
    assert steps["judging-scorecard"]["ok"] is True
    assert steps["local-runtime-proof"]["skipped"] is True
    assert steps["frontend-build-proof"]["skipped"] is True
    assert "demo_shot.Requirement draft flow" in report["requiredFailures"]

    markdown = markdown_reports[0].read_text(encoding="utf-8-sig")
    assert "Qwen Cloud Judge Rehearsal" in markdown
    assert "Seeded Memory Hub claim review" in markdown
    assert "Fast Rehearsal Commands" in markdown
    assert "Final Submission Blockers" in markdown


def test_qwencloud_judge_rehearsal_registered_in_submission_flow() -> None:
    script_path = "scripts/qwencloud-judge-rehearsal.ps1"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-gap-list.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-judging-scorecard.ps1",
        "scripts/qwencloud-hackathon-submission-packet.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")
