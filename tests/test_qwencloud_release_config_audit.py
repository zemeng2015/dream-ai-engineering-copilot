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


def test_release_config_audit_accepts_code_package_route_without_acr(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    secret_value = "fixture-qwen-key-should-not-leak"
    env_file.write_text(
        "\n".join(
            [
                "ALIBABA_CLOUD_ACCESS_KEY_ID=fixture-access-key",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET=fixture-secret-key",
                "ALIBABA_CLOUD_REGION=ap-southeast-1",
                "ALIBABA_CLOUD_RUNTIME_REGION=ap-southeast-1",
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
            "-UseCodePackage",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report_path = sorted(output_dir.glob("release-config-audit-*.json"))[0]
    raw_report = report_path.read_text(encoding="utf-8-sig")
    report = json.loads(raw_report)

    assert report["status"] == "READY"
    assert report["deploymentMode"] == "custom-runtime-code-package"
    assert report["effectiveRuntimeRegion"] == "ap-southeast-1"
    assert secret_value not in raw_report
    assert _check(report, "env.ALIBABA_CLOUD_RUNTIME_REGION.effective")["ok"] is True
    assert _check(report, "env.ALIBABA_CLOUD_CONTAINER_IMAGE.not_required_for_code_package")[
        "ok"
    ] is True
    assert _check(report, "serverless_runtime_template.uses_custom_debian11")["ok"] is True
    assert _check(report, "serverless_runtime_template.uses_fc_python312")["ok"] is True
    assert _check(
        report, "serverless_runtime_template.uses_bounded_non_thinking_qwen"
    )["ok"] is True
    assert _check(
        report, "serverless_runtime_template.uses_singapore_dashscope_endpoint"
    )["ok"] is True
    assert _check(
        report, "serverless_runtime_template.no_unvalidated_endpoint_override"
    )["ok"] is True
    assert _check(report, "serverless_runtime_template.no_acr_image_dependency")["ok"] is True
    assert _check(report, "serverless_runtime_template.uses_writable_ephemeral_paths")[
        "ok"
    ] is True
    assert _check(report, "serverless_runtime_template.caps_function_concurrency")[
        "ok"
    ] is True
    assert all(
        not item["name"].startswith("env.ALIBABA_CLOUD_CONTAINER_IMAGE.present")
        for item in report["checks"]
    )


def test_release_config_audit_rejects_unofficial_endpoint_and_model(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    env_file.write_text(
        "\n".join(
            [
                "ALIBABA_CLOUD_ACCESS_KEY_ID=fixture-access-key",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET=fixture-secret-key",
                "ALIBABA_CLOUD_RUNTIME_REGION=ap-southeast-1",
                "DASHSCOPE_API_KEY=fixture-qwen-key",
                "QWEN_BASE_URL=https://collector.example/compatible-mode/v1",
                "QWEN_MODEL=qwen-other-model",
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
            "-UseCodePackage",
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
    assert _check(report, "env.QWEN_BASE_URL.key_url_alignment")["ok"] is False
    assert _check(report, "env.QWEN_MODEL.submission_alignment")["ok"] is False


def test_release_config_audit_rejects_cross_region_code_package(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    env_file = tmp_path / ".env.qwencloud.local"
    env_file.write_text(
        "\n".join(
            [
                "ALIBABA_CLOUD_ACCESS_KEY_ID=fixture-access-key",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET=fixture-secret-key",
                "ALIBABA_CLOUD_RUNTIME_REGION=cn-hangzhou",
                "DASHSCOPE_API_KEY=fixture-qwen-key",
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
            "-UseCodePackage",
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
    assert _check(report, "env.ALIBABA_CLOUD_RUNTIME_REGION.effective")["ok"] is False


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
    assert "function Quote-ProcessArg" in final_readiness
    assert "function Invoke-PowerShellProcess" in final_readiness
    assert "-ArgumentList $quotedArguments" in final_readiness
    assert "-ArgumentList $args" not in final_readiness
    assert script_name in final_bundle
    assert "release_config_audit_ready" in final_bundle
    assert "release_config_audit_markdown" in final_bundle
    assert "release_config_audit_json" in final_bundle
    assert "release-config-audit" in final_action_board
    assert "releaseConfigReady" in final_action_board
    assert "Fix release config audit" in final_action_board
    assert "function Quote-ProcessArg" in final_action_board
    assert "function Invoke-PowerShellProcess" in final_action_board
    assert "-ArgumentList $quotedArguments" in final_action_board
    assert "-ArgumentList $Arguments" not in final_action_board


def test_fc_code_package_includes_same_origin_angular_build() -> None:
    package_script = (
        ROOT / "scripts/qwencloud-build-fc-code-package.ps1"
    ).read_text(encoding="utf-8-sig")

    assert "npm" in package_script
    assert "run build" in package_script
    assert 'frontend/dist/frontend/browser' in package_script
    assert 'frontendIncluded = $true' in package_script
    assert 'frontendFileCount = $frontendFileCount' in package_script
    assert 'docs/assets/qwen-memory-ab-benchmark-summary.json' in package_script
    assert 'docs/qwen-memory-ab-benchmark.md' in package_script
    assert 'docs/assets/qwen-experience-memory-benchmark-summary.json' in package_script
    assert 'docs/assets/qwen-experience-memory-benchmark-report.json' in package_script
    assert 'docs/qwen-experience-memory-benchmark.md' in package_script
    assert 'deploy/alibaba/requirements-fc312.lock.txt' in package_script
    assert 'docs/assets/qwencloud-tablestore-proof-summary.json' in package_script
    assert 'docs/qwencloud-tablestore-architecture.md' in package_script
    assert 'deploy/alibaba/ram/dream-qwencloud-fc-assume-role-policy.json' in package_script
    assert 'deploy/alibaba/ram/dream-qwencloud-tablestore-data-policy.json' in package_script
    assert 'tablestore/__init__.py' in package_script
    assert 'requirementsLockSha256' in package_script
    assert 'deploy/alibaba/serverless-devs-runtime.yaml' in package_script
    assert 'deploymentProof = "deploy/alibaba/serverless-devs-runtime.yaml"' in package_script
    assert '-SkipPipInstall is unsafe' in package_script
    assert 'cd "${CODE_ROOT}"' in package_script
    assert 'export PYTHONPATH=' in package_script
    assert 'FC_CUSTOM_LISTEN_PORT:-${PORT:-9000}' in package_script
    assert '/var/fc/lang/python3.12/bin/python3' in package_script


def test_fc_runtime_uses_temporary_role_credentials_for_one_tablestore_table() -> None:
    template = (ROOT / "deploy/alibaba/serverless-devs-runtime.yaml").read_text(
        encoding="utf-8-sig"
    )
    data_policy = json.loads(
        (
            ROOT
            / "deploy/alibaba/ram/dream-qwencloud-tablestore-data-policy.json"
        ).read_text(encoding="utf-8-sig")
    )
    trust_policy = json.loads(
        (
            ROOT / "deploy/alibaba/ram/dream-qwencloud-fc-assume-role-policy.json"
        ).read_text(encoding="utf-8-sig")
    )

    assert (
        "role: acs:ram::${env('ALIBABA_CLOUD_ACCOUNT_ID')}:"
        "role/dream-qwencloud-fc-role"
    ) in template
    assert "DREAM_EXPERIENCE_STORE: tablestore" in template
    assert "DREAM_BUILD_SHA: ${env('DREAM_BUILD_SHA')}" in template
    assert "DREAM_BUILD_SHA: uncommitted" not in template
    assert "instanceConcurrency: 20" in template
    assert "reservedConcurrency: 20" in template
    assert "ALIBABA_CLOUD_ACCESS_KEY_ID:" not in template
    assert "ALIBABA_CLOUD_ACCESS_KEY_SECRET:" not in template

    statement = data_policy["Statement"]
    assert len(statement) == 1
    assert statement[0]["Effect"] == "Allow"
    assert set(statement[0]["Action"]) == {
        "ots:GetRow",
        "ots:GetRange",
        "ots:PutRow",
        "ots:StartLocalTransaction",
        "ots:CommitTransaction",
        "ots:AbortTransaction",
    }
    assert statement[0]["Resource"].endswith(
        ":instance/dreammem/table/dream_experience_v1"
    )
    assert trust_policy["Statement"] == [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": ["fc.aliyuncs.com"]},
        }
    ]


def test_runtime_release_validates_workspace_url_before_deploy() -> None:
    release_script = (
        ROOT / "scripts/qwencloud-alibaba-runtime-release.ps1"
    ).read_text(encoding="utf-8-sig")

    assert "$requiredEnv = @(" in release_script
    for required_env in (
        "DASHSCOPE_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_MODEL",
        "ALIBABA_CLOUD_ACCOUNT_ID",
    ):
        assert f'"{required_env}"' in release_script
    assert '"deploy/alibaba/ram/dream-qwencloud-fc-assume-role-policy.json"' in release_script
    assert '"deploy/alibaba/ram/dream-qwencloud-tablestore-data-policy.json"' in release_script
    assert "DREAM_BUILD_SHA" in release_script
    assert '"scripts/qwencloud-release-config-audit.ps1"' in release_script
    assert '-Name "release-config-audit"' in release_script
    assert "$AllowDraftPacket -or" not in release_script
    assert "Protect-SensitiveLogText" in release_script
    assert "Protect-ServerlessDevsLogs" in release_script
    assert "system_url:" in release_script
    assert "\\.fcapp\\.run" in release_script
