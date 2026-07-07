# SPDX-License-Identifier: Apache-2.0

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


def _run_video_status(
    tmp_path: Path,
    url: str,
    allow_draft: bool = False,
) -> subprocess.CompletedProcess[str]:
    exe = _powershell()
    args = [exe, "-NoProfile"]
    if sys.platform == "win32":
        args += ["-ExecutionPolicy", "Bypass"]
    args += [
        "-File",
        str(ROOT / "scripts" / "qwencloud-video-upload-status.ps1"),
        "-DemoVideoUrl",
        url,
        "-OutputDir",
        str(tmp_path),
        "-SkipLocalVideoChecks",
        "-SkipExternalUrlChecks",
    ]
    if allow_draft:
        args.append("-AllowDraft")

    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _latest_status_json(tmp_path: Path) -> dict[str, object]:
    report = sorted(tmp_path.glob("video-upload-status-*.json"))[-1]
    return json.loads(report.read_text(encoding="utf-8-sig"))


def _check(report: dict[str, object], name: str) -> dict[str, object]:
    checks = report["checks"]
    assert isinstance(checks, list)
    for item in checks:
        assert isinstance(item, dict)
        if item["name"] == name:
            return item
    raise AssertionError(f"missing check: {name}")


def test_video_status_accepts_devpost_facebook_video_url(tmp_path: Path) -> None:
    result = _run_video_status(tmp_path, "https://www.facebook.com/watch/?v=123456789")

    assert result.returncode == 0, result.stdout + result.stderr
    report = _latest_status_json(tmp_path)
    assert report["readyForDevpostVideoField"] is True
    assert _check(report, "public_demo_video_url_platform")["ok"] is True


def test_video_status_rejects_youku_after_devpost_rule_refresh(tmp_path: Path) -> None:
    result = _run_video_status(
        tmp_path,
        "https://v.youku.com/v_show/id_XNzk0ODI1.html",
        allow_draft=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = _latest_status_json(tmp_path)
    assert report["readyForDevpostVideoField"] is False
    assert _check(report, "public_demo_video_url_platform")["ok"] is False
