# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-official-source-refresh.ps1"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def test_official_source_refresh_detects_current_devpost_requirements(tmp_path) -> None:
    overview = tmp_path / "overview.html"
    rules = tmp_path / "rules.html"
    output_dir = tmp_path / "qwencloud-proof"

    overview.write_text(
        """
        Deadline: Jul 9, 2026 @ 2:00pm PDT
        Requirements: Build a project using Qwen models available on Qwen Cloud.
        Track 1: MemoryAgent Build an Agent with persistent memory that recalls
        critical memories within limited context windows.
        What to submit: Provide a URL to your code repository for judging and
        testing. The repository must be public and open source.
        Include Proof of Alibaba Cloud Deployment on Alibaba Cloud.
        Include an Architecture Diagram showing how Qwen Cloud connects to
        backend, database, and frontend.
        Include a video about 3 minutes uploaded to YouTube, Vimeo, or Facebook Video.
        Judging Criteria: Technical Depth & Engineering (30%),
        Innovation & AI Creativity (30%), Problem Value & Impact (25%),
        Presentation & Documentation (15%). Blog Post Prize.
        """,
        encoding="utf-8",
    )
    rules.write_text(
        """
        Submission Period: May 26, 2026 (8:00 am Pacific Time) - Jul 9, 2026(2:00 pm Pacific Time).
        Project Requirements: Entrants must build a project using Qwen models
        available on Qwen Cloud.
        Track 1: MemoryAgent Build an Agent with persistent memory.
        Submission Requirements: Include Proof of Alibaba Cloud Deployment.
        Include a demonstration video that should be less than three (3) minutes.
        The video must be uploaded to YouTube, Vimeo, or Youku.
        Access must be provided to an Entrant's working Project for judging and testing.
        Innovation & AI Creativity (30%). Technical Depth & Engineering (30%).
        Problem Value & Impact (25%). Presentation & Documentation (15%).
        """,
        encoding="utf-8",
    )

    command = _powershell_command() + [
        "-File",
        str(SCRIPT),
        "-OutputDir",
        str(output_dir),
        "-OverviewHtmlPath",
        str(overview),
        "-RulesHtmlPath",
        str(rules),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    reports = sorted(output_dir.glob("official-source-refresh-*.json"))
    markdown_reports = sorted(output_dir.glob("official-source-refresh-*.md"))
    assert len(reports) == 1
    assert len(markdown_reports) == 1

    report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
    checks = {item["name"]: item for item in report["checks"]}

    assert report["status"] == "READY"
    assert report["readyForOfficialSourceSnapshot"] is True
    assert report["acceptedVideoPlatformUnion"] == [
        "YouTube",
        "Vimeo",
        "Facebook Video",
        "Youku",
    ]
    assert checks["video_platform_overview_facebook_present"]["ok"] is True
    assert checks["video_platform_rules_youku_present"]["ok"] is True
    assert checks["judging_weights_present"]["ok"] is True

    markdown = markdown_reports[0].read_text(encoding="utf-8-sig")
    assert "Video Platform Note" in markdown
    assert "YouTube, Vimeo, and Youku" in markdown


def test_official_source_refresh_registered_in_submission_flow() -> None:
    script_path = "scripts/qwencloud-official-source-refresh.ps1"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-gap-list.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-finalize-after-urls.ps1",
        "scripts/qwencloud-judging-scorecard.ps1",
        "scripts/qwencloud-hackathon-submission-packet.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")


def test_finalize_after_urls_refreshes_official_sources_before_final_gates() -> None:
    finalizer = (ROOT / "scripts" / "qwencloud-finalize-after-urls.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "[switch]$SkipOfficialSourceRefresh" in finalizer
    assert '"scripts/qwencloud-official-source-refresh.ps1"' in finalizer
    assert '"official-source-refresh"' in finalizer
    assert '"video-upload-status"' in finalizer
    assert finalizer.index('"official-source-refresh"') < finalizer.index(
        '"video-upload-status"'
    )
    assert "officialSourceJson" in finalizer
