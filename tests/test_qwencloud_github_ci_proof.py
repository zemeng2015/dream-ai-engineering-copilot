# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-github-ci-proof.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_github_ci_proof_accepts_fixture_for_current_head(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    repo_json = tmp_path / "repo.json"
    runs_json = tmp_path / "runs.json"
    head = "abc123fixture"

    repo_json.write_text(
        json.dumps(
            {
                "nameWithOwner": "zemeng2015/dream-ai-engineering-copilot",
                "visibility": "PUBLIC",
                "isPrivate": False,
                "url": "https://github.com/zemeng2015/dream-ai-engineering-copilot",
                "licenseInfo": {"key": "apache-2.0", "name": "Apache License 2.0"},
                "defaultBranchRef": {"name": "main"},
            }
        ),
        encoding="utf-8",
    )
    runs_json.write_text(
        json.dumps(
            [
                {
                    "databaseId": 12345,
                    "headSha": head,
                    "status": "completed",
                    "conclusion": "success",
                    "displayTitle": "Fixture CI",
                    "url": "https://github.com/example/actions/runs/12345",
                    "workflowName": "main CI",
                }
            ]
        ),
        encoding="utf-8",
    )

    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-RepoJsonPath",
        str(repo_json),
        "-RunsJsonPath",
        str(runs_json),
        "-GitHead",
        head,
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("github-ci-proof-*.json"))
    markdown_reports = sorted(output_dir.glob("github-ci-proof-*.md"))
    assert len(reports) == 1
    assert len(markdown_reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    checks = {item["name"]: item for item in report["checks"]}

    assert report["status"] == "READY"
    assert report["readyForGitHubCiProof"] is True
    assert report["usingFixtures"] is True
    assert checks["repo_public"]["ok"] is True
    assert checks["repo_license_apache_2_0"]["ok"] is True
    assert checks["ci_run_for_head_present"]["ok"] is True
    assert checks["ci_run_completed_success"]["ok"] is True


def test_github_ci_proof_registered_in_final_submission_flow() -> None:
    script_path = "scripts/qwencloud-github-ci-proof.ps1"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")

    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    assert "github_ci_proof_ready" in final_bundle
    assert "github_ci_proof_markdown" in final_bundle
    assert "github_ci_proof_json" in final_bundle
