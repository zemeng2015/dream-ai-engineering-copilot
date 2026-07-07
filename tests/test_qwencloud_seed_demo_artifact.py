# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud_seed_demo_artifact.py"


def test_qwencloud_seed_demo_artifact_builds_approved_memory_package(tmp_path) -> None:
    output_dir = tmp_path / "qwencloud-proof"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(output_dir),
            "--promote-count",
            "3",
            "--top-k",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summaries = sorted(output_dir.glob("seeded-demo-artifact-*/seeded-demo-summary.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))

    ledger_path = Path(summary["ledgerPath"])
    latest_scan_path = Path(summary["latestScanPath"])
    context_card_path = Path(summary["contextCardPath"])
    zip_path = Path(summary["zipPath"])

    assert summary["status"] == "READY"
    assert summary["readyForJudgeDemo"] is True
    assert summary["teamId"] == "demo_team"
    assert summary["repoName"] == "dfp-demo-repo"
    assert len(summary["reviewEvents"]) == 3
    assert summary["searchResultCount"] >= 3
    assert ledger_path.exists()
    assert latest_scan_path.exists()
    assert context_card_path.exists()
    assert zip_path.exists()

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert len(ledger["events"]) == 3
    assert {event["new_status"] for event in ledger["events"]} == {"approved"}
    assert {event["reviewer"] for event in ledger["events"]} == {"qwencloud-demo-seed"}

    context_card = context_card_path.read_text(encoding="utf-8")
    assert "DREAM Memory Context Card" in context_card
    assert "Approved claims" in context_card
    assert "heuristic_semantic" in context_card


def test_qwencloud_seed_demo_artifact_registered_in_submission_flow() -> None:
    script_path = "scripts/qwencloud_seed_demo_artifact.py"

    for path in [
        "README.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-gap-list.md",
        "docs/qwencloud-final-5min-checklist.md",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-judging-scorecard.ps1",
    ]:
        assert script_path in (ROOT / path).read_text(encoding="utf-8-sig")
