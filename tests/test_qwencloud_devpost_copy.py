# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "docs" / "qwencloud-devpost-story.md"
HELPER = ROOT / "scripts" / "qwencloud-devpost-copy.ps1"
PAYLOAD = ROOT / "scripts" / "qwencloud-devpost-draft-payload.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_canonical_devpost_story_contains_v3_cloud_proof() -> None:
    story = STORY.read_text(encoding="utf-8")

    for claim in [
        "Alibaba Tablestore",
        "cross-instance",
        "20/20",
        "19 of 64",
        "production-effectiveness claims",
    ]:
        assert claim in story
    assert "SQLite" not in story


def test_structured_payload_uses_canonical_devpost_story(tmp_path: Path) -> None:
    output_dir = tmp_path / "proof"
    architecture = tmp_path / "architecture.png"
    screenshot = tmp_path / "alibaba.png"
    architecture.write_bytes(b"fixture")
    screenshot.write_bytes(b"fixture")

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(PAYLOAD),
            "-OutputDir",
            str(output_dir),
            "-DemoVideoUrl",
            "https://youtu.be/dreamv3fixture",
            "-BackendUrl",
            "https://dream-qwencloud.example.com",
            "-ArchitectureUploadPath",
            str(architecture),
            "-AlibabaScreenshotPath",
            str(screenshot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report_path = next(output_dir.glob("devpost-draft-payload-*.json"))
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    fields = {field["elementId"]: field for field in report["fields"]}
    story = STORY.read_text(encoding="utf-8").strip()

    assert fields["software_description"]["value"] == story
    assert "Alibaba Cloud Tablestore" in fields["software_tag_list"]["value"]
    assert "SQLite" not in fields["software_tag_list"]["value"]
    assert report["publicCopy"]["story"] == story
    assert len(report["publicCopy"]["storySha256"]) == 64
    assert "project_story_v3_cloud_proof" not in report["requiredFailures"]


def test_devpost_copy_helper_is_packaged_with_story() -> None:
    helper = HELPER.read_text(encoding="utf-8-sig")
    bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "Get-QwenCloudDevpostCopy" in helper
    assert 'Add-Item -Name "devpost_story_source"' in bundle
    assert 'Add-Item -Name "devpost_copy_helper"' in bundle
