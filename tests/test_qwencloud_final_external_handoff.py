# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-final-external-handoff.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_qwencloud_final_external_handoff_builds_safe_pack(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-SkipOfficialSourceRefresh",
        "-SkipVideoPublication",
        "-SkipGitHubSecrets",
        "-SkipActionBoard",
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
    reports = sorted(output_dir.glob("external-handoff-*.json"))
    markdown_reports = sorted(output_dir.glob("external-handoff-*.md"))
    zips = sorted(output_dir.glob("external-handoff-*.zip"))
    assert len(reports) == 1
    assert len(markdown_reports) == 1
    assert len(zips) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    steps = {step["name"]: step for step in report["steps"]}
    confirmations = {item["name"]: item for item in report["actionTimeConfirmations"]}

    assert report["status"] == "READY"
    assert report["readyForExternalHandoff"] is True
    assert Path(report["commandsPath"]).exists()
    assert Path(report["zipPath"]).exists()
    assert steps["video-publication-handoff"]["status"] == "skipped"
    assert steps["official-source-refresh"]["status"] == "skipped"
    assert steps["cloud-credentials-handoff"]["status"] == "draft"
    assert steps["devpost-draft-payload"]["status"] == "draft"
    assert steps["github-secrets-handoff"]["status"] == "skipped"
    assert confirmations["Final Devpost legal submit"]["owner"] == "Zack only"

    markdown = markdown_reports[0].read_text(encoding="utf-8-sig")
    commands = Path(report["commandsPath"]).read_text(encoding="utf-8-sig")
    assert "Safety Boundary" in markdown
    assert "Action-Time Confirmations" in markdown
    assert "Final Devpost legal submit" in markdown
    assert "qwencloud-post-submit-verification.ps1" in commands
    assert "qwencloud-final-completion-evidence.ps1" in commands
    assert "s config add -a default --AccessKeyID" not in commands
    assert '"--AccessKeyID", $env:ALIBABA_CLOUD_ACCESS_KEY_ID' in commands
    assert '"--AccessKeySecret", $env:ALIBABA_CLOUD_ACCESS_KEY_SECRET' in commands
    assert "& s @sConfigArgs" in commands


def test_qwencloud_final_external_handoff_registered_in_submission_flow() -> None:
    script_path = "scripts/qwencloud-final-external-handoff.ps1"

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


def test_final_action_board_uses_env_driven_serverless_devs_access() -> None:
    action_board = (ROOT / "scripts" / "qwencloud-final-action-board.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "Configure local Alibaba release environment" in action_board
    assert "s config add -a default --AccessKeyID" not in action_board
    assert '"--AccessKeyID", $env:ALIBABA_CLOUD_ACCESS_KEY_ID' in action_board
    assert '"--AccessKeySecret", $env:ALIBABA_CLOUD_ACCESS_KEY_SECRET' in action_board
    assert "& s @sConfigArgs" in action_board


def test_final_action_board_exposes_action_confirmation_fields() -> None:
    action_board = (ROOT / "scripts" / "qwencloud-final-action-board.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "$requiresConfirmation = [bool]$RequiresUser" in action_board
    assert "requiresUser = $requiresConfirmation" in action_board
    assert "requiresZackConfirmation = $requiresConfirmation" in action_board
    assert "requiresActionTimeConfirmation = $requiresConfirmation" in action_board
