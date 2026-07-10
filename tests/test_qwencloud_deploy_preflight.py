# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _powershell() -> str:
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        pytest.skip("PowerShell is not available")
    return exe


def test_deploy_preflight_allow_draft_writes_report_without_cloud_env(tmp_path: Path) -> None:
    exe = _powershell()
    args = [exe, "-NoProfile"]
    if sys.platform == "win32":
        args += ["-ExecutionPolicy", "Bypass"]
    args += [
        "-File",
        str(ROOT / "scripts" / "qwencloud-deploy-preflight.ps1"),
        "-ProjectRoot",
        str(ROOT),
        "-OutputDir",
        str(tmp_path),
        "-AllowDraft",
    ]

    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stdout + result.stderr
    report = sorted(tmp_path.glob("deploy-preflight-*.json"))[-1]
    data = json.loads(report.read_text(encoding="utf-8-sig"))
    checks = {item["name"]: item for item in data["checks"]}

    assert data["allowDraft"] is True
    assert data["readyForDeploy"] is False
    assert data["deploymentMode"] == "custom-runtime-code-package"
    assert data["buildImage"] is False
    assert data["smokeContainer"] is False
    assert data["gitCommit"]
    assert checks["file.Dockerfile"]["ok"] is True
    assert checks["docker.build"]["required"] is False
    assert checks["docker.smoke_port_available"]["required"] is False
    assert checks["docker.smoke_container"]["required"] is False
    assert checks["docker.smoke_showcase"]["required"] is False
    assert checks["env.ALIBABA_CLOUD_CONTAINER_IMAGE"]["ok"] is True
    assert checks["env.ALIBABA_CLOUD_CONTAINER_IMAGE"]["required"] is False
    assert checks["file.deploy/alibaba/serverless-devs-runtime.yaml"]["ok"] is True
