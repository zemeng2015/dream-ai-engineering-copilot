# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-devpost-handoff.ps1"
REPO_REF = "codex/champion-memory-loop"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_devpost_handoff_treats_env_placeholders_as_missing(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    env_file.write_text(
        "\n".join(
            [
                "DASHSCOPE_API_KEY=<qwen-cloud-api-key>",
                "ALIBABA_CLOUD_REGION=ap-southeast-1",
                "ALIBABA_CLOUD_CONTAINER_IMAGE=<registry-host>/<namespace>/dream-qwencloud-memoryagent:latest",
            ]
        ),
        encoding="utf-8",
    )

    architecture = tmp_path / "architecture.png"
    demo_video = tmp_path / "demo.mp4"
    alibaba_screenshot = tmp_path / "alibaba.png"
    alibaba_video = tmp_path / "alibaba.mp4"
    for path in [architecture, demo_video, alibaba_screenshot, alibaba_video]:
        path.write_bytes(b"placeholder")

    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-RepoRef",
        REPO_REF,
        "-EnvFile",
        str(env_file),
        "-DemoVideoUrl",
        "https://youtu.be/example",
        "-ArchitectureUploadPath",
        str(architecture),
        "-LocalDemoVideoPath",
        str(demo_video),
        "-AlibabaScreenshotPath",
        str(alibaba_screenshot),
        "-AlibabaProofVideoPath",
        str(alibaba_video),
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
    reports = sorted(output_dir.glob("devpost-handoff-*.json"))
    assert len(reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))

    assert report["status"] == "DRAFT"
    assert "DASHSCOPE_API_KEY" in report["importedEnvNames"]
    assert "env.DASHSCOPE_API_KEY" in report["blockers"]
    assert "env.ALIBABA_CLOUD_CONTAINER_IMAGE" in report["blockers"]
    assert "env.ALIBABA_CLOUD_REGION" not in report["blockers"]
    assert report["repoRef"] == REPO_REF
    assert report["sourceCodeUrl"].endswith(f"/tree/{REPO_REF}")
    assert report["copyFields"]["repoUrl"].endswith(f"/tree/{REPO_REF}")
    assert f"/blob/{REPO_REF}/LICENSE" in report["copyFields"]["licenseUrl"]
    assert "Alibaba Tablestore" in report["copyFields"]["description"]
    assert "cross-instance" in report["copyFields"]["description"]
    assert "20/20" in report["copyFields"]["description"]
    assert "SQLite" not in report["copyFields"]["description"]
    assert "Alibaba Cloud Tablestore" in report["copyFields"]["builtWith"]
    assert len(report["copyFields"]["storySha256"]) == 64
