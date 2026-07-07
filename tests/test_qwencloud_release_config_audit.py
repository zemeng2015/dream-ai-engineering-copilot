# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-release-config-audit.ps1"


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


def test_release_config_audit_accepts_valid_env_without_leaking_values(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    secret_value = "fixture-qwen-key-should-not-leak"
    env_file.write_text(
        "\n".join(
            [
                "ALIBABA_CLOUD_ACCESS_KEY_ID=fixture-access-key",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET=fixture-secret-key",
                "ALIBABA_CLOUD_REGION=ap-southeast-1",
                (
                    "ALIBABA_CLOUD_CONTAINER_IMAGE="
                    "registry-intl.ap-southeast-1.aliyuncs.com/dream/dream-qwencloud-memoryagent:ci"
                ),
                "ALIBABA_CONTAINER_REGISTRY_USERNAME=fixture-user",
                "ALIBABA_CONTAINER_REGISTRY_PASSWORD=fixture-password",
                f"DASHSCOPE_API_KEY={secret_value}",
                "QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "QWEN_MODEL=qwen3.7-plus",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-EnvFile",
            str(env_file),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("release-config-audit-*.json"))
    assert len(reports) == 1

    raw_report = reports[0].read_text(encoding="utf-8-sig")
    report = json.loads(raw_report)
    assert report["status"] == "READY"
    assert report["readyForReleaseConfig"] is True
    assert secret_value not in raw_report
    assert _check(report, "env.ALIBABA_CLOUD_REGION.format")["ok"] is True
    assert _check(report, "env.ALIBABA_CLOUD_CONTAINER_IMAGE.format")["ok"] is True
    assert _check(report, "workflow.generates_release_summary_after_bundle")["ok"] is True


def test_release_config_audit_rejects_placeholder_env(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    env_file.write_text(
        "\n".join(
            [
                "ALIBABA_CLOUD_REGION=<region>",
                "ALIBABA_CLOUD_CONTAINER_IMAGE=<registry-host>/<namespace>/dream-qwencloud-memoryagent:latest",
                "DASHSCOPE_API_KEY=<qwen-cloud-api-key>",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-EnvFile",
            str(env_file),
            "-AllowDraft",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(
        sorted(output_dir.glob("release-config-audit-*.json"))[0].read_text(
            encoding="utf-8-sig"
        )
    )

    assert report["status"] == "DRAFT"
    assert report["readyForReleaseConfig"] is False
    assert _check(report, "env.DASHSCOPE_API_KEY.present")["ok"] is False
    assert _check(report, "env.ALIBABA_CLOUD_REGION.format")["ok"] is False
    assert _check(report, "env.ALIBABA_CLOUD_CONTAINER_IMAGE.format")["ok"] is False


def test_release_config_audit_registered_in_final_flow() -> None:
    script_name = "scripts/qwencloud-release-config-audit.ps1"
    assert SCRIPT.exists()

    final_readiness = (ROOT / "scripts/qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts/qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_action_board = (
        ROOT / "scripts/qwencloud-final-action-board.ps1"
    ).read_text(encoding="utf-8-sig")

    assert script_name in final_readiness
    assert "release_config_audit_ready" in final_readiness
    assert script_name in final_bundle
    assert "release_config_audit_ready" in final_bundle
    assert "release_config_audit_markdown" in final_bundle
    assert "release_config_audit_json" in final_bundle
    assert "release-config-audit" in final_action_board
    assert "releaseConfigReady" in final_action_board
    assert "Fix release config audit" in final_action_board
