# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-cloud-credentials-handoff.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_cloud_credentials_template_does_not_shadow_process_env(tmp_path: Path) -> None:
    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(tmp_path),
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
    report_path = sorted(tmp_path.glob("cloud-credentials-handoff-*.json"))[-1]
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    template = Path(report["template"]).read_text(encoding="utf-8-sig")
    markdown = Path(report["markdown"]).read_text(encoding="utf-8-sig")

    assert "$env:DASHSCOPE_API_KEY" in template
    assert "$env:ALIBABA_CONTAINER_REGISTRY_USERNAME" in template
    assert "$env:ALIBABA_CONTAINER_REGISTRY_PASSWORD" in template
    assert "--password-stdin" in template
    assert "intentionally omits -EnvFile" in template
    assert "qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer" in template
    assert "qwencloud-alibaba-release.ps1 -DemoVideoUrl" in template
    assert "-EnvFile .env.qwencloud.local" not in template
    assert all("-EnvFile .env.qwencloud.local" not in item for item in report["nextCommands"])
    assert "placeholder .env.qwencloud.local values cannot override" in markdown
