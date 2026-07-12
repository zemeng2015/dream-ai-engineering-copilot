# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-final-completion-evidence.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_final_completion_evidence_packages_ready_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()
    backend_url = "https://dream-memoryagent.example.com"
    video_url = "https://www.youtube.com/watch?v=abc123fixture"
    devpost_url = "https://devpost.com/software/dream-qwen-cloud-memoryagent"

    post_json = output_dir / "devpost-post-submit-verification-20260707-120000.json"
    post_md = output_dir / "devpost-post-submit-verification-20260707-120000.md"
    post_json.write_text(
        json.dumps(
            {
                "status": "READY",
                "readyForGoalCompletionEvidence": True,
                "devpostProjectUrl": devpost_url,
                "demoVideoUrl": video_url,
                "backendUrl": backend_url,
            }
        ),
        encoding="utf-8",
    )
    post_md.write_text("# Post submit\n", encoding="utf-8")

    rules_json = output_dir / "official-rules-gate-20260707-120000.json"
    rules_md = output_dir / "official-rules-gate-20260707-120000.md"
    rules_json.write_text(
        json.dumps({"status": "READY", "readyForOfficialRules": True}),
        encoding="utf-8",
    )
    rules_md.write_text("# Official rules\n", encoding="utf-8")

    scorecard_json = output_dir / "judging-scorecard-20260707-120000.json"
    scorecard_md = output_dir / "judging-scorecard-20260707-120000.md"
    scorecard_json.write_text(
        json.dumps({"status": "READY", "readyForJudgingNarrative": True}),
        encoding="utf-8",
    )
    scorecard_md.write_text("# Judging scorecard\n", encoding="utf-8")

    packet_json = output_dir / "devpost-submission-packet-20260707-120000.json"
    packet_md = output_dir / "devpost-submission-packet-20260707-120000.md"
    packet_json.write_text(
        json.dumps({"readyForDevpost": True}),
        encoding="utf-8",
    )
    packet_md.write_text("# Submission packet\n", encoding="utf-8")

    summary_json = output_dir / "release-summary-20260707-120001.json"
    summary_md = output_dir / "release-summary-20260707-120001.md"
    summary_json.write_text(
        json.dumps(
            {
                "status": "READY",
                "readyForFinalSubmit": True,
                "demoVideoUrl": video_url,
                "backendUrl": backend_url,
                "finalBundle": {},
            }
        ),
        encoding="utf-8",
    )
    summary_md.write_text("# Release summary\n", encoding="utf-8")

    bundle_dir = output_dir / "final-upload-bundle-20260707-120002-001"
    bundle_dir.mkdir()
    bundle_zip = output_dir / "final-upload-bundle-20260707-120002-001.zip"
    bundle_zip.write_bytes(b"final bundle")
    manifest_json = bundle_dir / "manifest.json"
    manifest_md = bundle_dir / "manifest.md"
    manifest_json.write_text(
        json.dumps(
            {
                "readyForUpload": True,
                "zipPath": str(bundle_zip),
                "gitCommit": "abc123fixture",
                "gitWorktreeClean": True,
                "gitRemoteSynced": True,
                "missingRequiredItems": [],
            }
        ),
        encoding="utf-8",
    )
    manifest_md.write_text("# Manifest\n", encoding="utf-8")

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-ReleaseSummaryJson",
            str(summary_json),
            "-FinalBundleManifest",
            str(manifest_json),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("final-completion-evidence-*.json"))
    archives = sorted(output_dir.glob("final-completion-evidence-*.zip"))
    assert len(reports) == 1
    assert len(archives) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    assert report["status"] == "READY"
    assert report["readyForGoalCompletionArchive"] is True
    assert report["devpostProjectUrl"] == devpost_url
    assert report["finalBundleZipSha256"]

    with zipfile.ZipFile(archives[0]) as archive:
        names = archive.namelist()
    assert any(name.endswith("manifest.json") for name in names)
    assert any(name.endswith(post_json.name) for name in names)
    assert any(name.endswith(rules_json.name) for name in names)
    assert any(name.endswith(scorecard_json.name) for name in names)
    assert any(name.endswith(packet_json.name) for name in names)
    assert any(name.endswith(summary_json.name) for name in names)
    assert any(name.endswith(bundle_zip.name) for name in names)


def test_final_completion_evidence_stays_draft_until_post_submit_ready(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()
    (output_dir / "devpost-post-submit-verification-20260707-120000.json").write_text(
        json.dumps({"status": "DRAFT", "readyForGoalCompletionEvidence": False}),
        encoding="utf-8",
    )

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(output_dir),
            "-AllowDraft",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(
        sorted(output_dir.glob("final-completion-evidence-*.json"))[0].read_text(
            encoding="utf-8-sig"
        )
    )

    assert report["status"] == "DRAFT"
    assert report["readyForGoalCompletionArchive"] is False
    assert "post_submit_verification_ready" in report["requiredFailures"]
    assert "official_rules_gate_ready" in report["requiredFailures"]
    assert "judging_scorecard_ready" in report["requiredFailures"]
    assert "submission_packet_ready" in report["requiredFailures"]
    assert "release_summary_present" not in report["requiredFailures"]
    assert "final_bundle_manifest_present" not in report["requiredFailures"]


def test_final_completion_evidence_registered_in_submission_flow() -> None:
    script_name = "scripts/qwencloud-final-completion-evidence.ps1"
    final_bundle = (ROOT / "scripts/qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    publish_playbook = (ROOT / "docs/qwencloud-publish-playbook.md").read_text(
        encoding="utf-8-sig"
    )
    checklist = (ROOT / "docs/qwencloud-final-5min-checklist.md").read_text(
        encoding="utf-8-sig"
    )

    assert SCRIPT.exists()
    assert script_name in final_bundle
    assert "final_completion_evidence_script" in final_bundle
    assert script_name in publish_playbook
    assert script_name in checklist
