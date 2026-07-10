# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-run-local-proof.sh"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_bash_local_proof_script_contains_judge_smoke_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "set -euo pipefail" in text
    assert "trap cleanup EXIT" in text
    assert "-m uvicorn dream.api.app:app" in text
    assert "/health" in text
    assert "Track 1: MemoryAgent" in text
    assert "qwen-cloud" in text
    assert "deploy/alibaba/serverless-devs-runtime.yaml" in text
    assert "tests/test_api_health.py tests/test_qwen_cloud_provider.py" in text
    assert "local-proof-bash-" in text
    assert "--skip-draft" in text
    assert "--allow-dirty" in text


def test_bash_local_proof_script_has_valid_bash_syntax() -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed in this environment")

    result = subprocess.run([bash, "-n", str(SCRIPT)], capture_output=True, text=True)
    if result.returncode != 0 and "WSL" in result.stderr and "/bin/bash" in result.stderr:
        pytest.skip("Windows WSL bash shim is present but no Linux bash is installed")
    assert result.returncode == 0, result.stderr


def test_bash_local_proof_is_registered_in_submission_flow() -> None:
    required_path = "scripts/qwencloud-run-local-proof.sh"

    for path in [
        ".github/workflows/ci.yml",
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-testing-and-rights-notes.md",
        "docs/qwencloud-publish-playbook.md",
        "docs/qwencloud-live-checklist.md",
        "scripts/qwencloud-hackathon-audit.ps1",
        "scripts/qwencloud-hackathon-submission-packet.ps1",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-judging-scorecard.ps1",
    ]:
        assert required_path in read(path)


def test_bash_local_proof_final_bundle_uses_named_asset() -> None:
    final_bundle = read("scripts/qwencloud-final-upload-bundle.ps1")

    assert "local_proof_bash_script" in final_bundle
    assert "local_proof_powershell_script" in final_bundle
