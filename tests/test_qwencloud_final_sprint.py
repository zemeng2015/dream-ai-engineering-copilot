# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_sprint_can_refresh_alibaba_proof_after_urls() -> None:
    final_sprint = (ROOT / "scripts" / "qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "[switch]$RefreshAlibabaProof" in final_sprint
    assert 'if ($RefreshAlibabaProof) { $finalizeArgs += "-RefreshAlibabaProof" }' in final_sprint
    assert "refreshAlibabaProof = [bool]$RefreshAlibabaProof" in final_sprint

    for path in [
        "docs/qwencloud-final-5min-checklist.md",
        "docs/qwencloud-live-checklist.md",
        "docs/qwencloud-publish-playbook.md",
    ]:
        text = (ROOT / path).read_text(encoding="utf-8-sig")
        assert "qwencloud-final-sprint.ps1" in text
        assert "-RefreshAlibabaProof" in text
