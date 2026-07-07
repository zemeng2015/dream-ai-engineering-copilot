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
    assert "finalizeSkippedForDraft = $true" in final_sprint
    assert (
        "skipped in draft mode until both DemoVideoUrl and BackendUrl are available"
        in final_sprint
    )
    assert "finalizeAfterUrlsSkippedForDraft = [bool]$finalizeSkippedForDraft" in final_sprint
    assert "[int]$StepTimeoutSeconds = 900" in final_sprint
    assert "$completed = $proc.WaitForExit($StepTimeoutSeconds * 1000)" in final_sprint
    assert "Stop-ProcessTree -ProcessId $proc.Id" in final_sprint
    assert "timeout after ${StepTimeoutSeconds}s; process tree stopped" in final_sprint
    assert "stepTimeoutSeconds = $StepTimeoutSeconds" in final_sprint
    assert '"- Step timeout seconds: $StepTimeoutSeconds"' in final_sprint
    assert 'Invoke-SprintStep -Name "final-sprint-release-summary"' in final_sprint
    assert "releaseSummaryReady" in final_sprint

    for path in [
        "docs/qwencloud-final-5min-checklist.md",
        "docs/qwencloud-live-checklist.md",
        "docs/qwencloud-publish-playbook.md",
    ]:
        text = (ROOT / path).read_text(encoding="utf-8-sig")
        assert "qwencloud-final-sprint.ps1" in text
        assert "-RefreshAlibabaProof" in text
