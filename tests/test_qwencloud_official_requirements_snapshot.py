# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "qwencloud-official-requirements-snapshot.md"


def test_official_requirements_snapshot_captures_current_devpost_requirements() -> None:
    text = SNAPSHOT.read_text(encoding="utf-8-sig")

    assert "Checked date: 2026-07-09" in text
    assert "https://qwencloud-hackathon.devpost.com/" in text
    assert "July 20, 2026 at 2:00pm PDT" in text
    assert "Track 1: MemoryAgent" in text
    assert "YouTube, Vimeo, or Facebook Video" in text
    assert "YouTube, Vimeo, or Youku" in text
    assert "short recording separate from" in text
    assert "deploy/alibaba/serverless-devs-runtime.yaml" in text
    assert "Technical Depth & Engineering: 30%" in text
    assert "Presentation & Documentation: 15%" in text


def test_official_requirements_snapshot_is_in_readiness_and_bundle_flow() -> None:
    official_gate = (ROOT / "scripts" / "qwencloud-official-rules-gate.ps1").read_text()
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text()
    final_readiness = (ROOT / "scripts" / "qwencloud-final-readiness.ps1").read_text()
    packet = (ROOT / "scripts" / "qwencloud-hackathon-submission-packet.ps1").read_text()

    assert "OfficialRequirementsSnapshotPath" in official_gate
    assert "official_requirements_snapshot" in official_gate
    assert "docs/qwencloud-official-requirements-snapshot.md" in final_bundle
    assert "docs/qwencloud-official-requirements-snapshot.md" in final_readiness
    assert "docs/qwencloud-official-requirements-snapshot.md" in packet
