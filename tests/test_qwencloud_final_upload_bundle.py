# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_upload_bundle_refreshes_action_board_for_each_bundle() -> None:
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert '[string]$RepoName = "zemeng2015/dream-ai-engineering-copilot"' in final_bundle
    assert "[switch]$SkipGitHubSecrets" in final_bundle
    assert "function Invoke-ActionBoard" in final_bundle
    assert "function Invoke-ExternalHandoff" in final_bundle
    assert '"scripts/qwencloud-final-action-board.ps1"' in final_bundle
    assert '"scripts/qwencloud-final-external-handoff.ps1"' in final_bundle
    assert '"-RepoName", $RepoName' in final_bundle
    assert 'if ($SkipGitHubSecrets) { $args += "-SkipGitHubSecrets" }' in final_bundle
    assert "$actionBoard = Invoke-ActionBoard" in final_bundle
    assert "$externalHandoff = Invoke-ExternalHandoff" in final_bundle
    assert (
        'Add-Item -Name "final_action_board_markdown" -Path $actionBoard.markdown'
        in final_bundle
    )
    assert (
        'Add-Item -Name "final_action_board_json" -Path $actionBoard.json'
        in final_bundle
    )
    assert (
        'Add-Item -Name "final_external_handoff_markdown" -Path $externalHandoff.markdown'
        in final_bundle
    )
    assert (
        'Add-Item -Name "final_external_handoff_json" -Path $externalHandoff.json'
        in final_bundle
    )
    assert (
        'Add-Item -Name "final_external_handoff_zip" -Path $externalHandoff.zip'
        in final_bundle
    )
    assert "latest_final_action_board_markdown" not in final_bundle
    assert "latest_final_action_board_json" not in final_bundle
    assert "latest_final_external_handoff_markdown" not in final_bundle
    assert "latest_final_external_handoff_json" not in final_bundle
    assert "latest_final_external_handoff_zip" not in final_bundle

    assert final_bundle.index("function Invoke-ActionBoard") < final_bundle.index(
        "$actionBoard = Invoke-ActionBoard"
    )
    assert final_bundle.index("$actionBoard = Invoke-ActionBoard") < final_bundle.index(
        "$externalHandoff = Invoke-ExternalHandoff"
    )
    assert final_bundle.index("$externalHandoff = Invoke-ExternalHandoff") < final_bundle.index(
        'Add-Item -Name "final_action_board_json"'
    )
    assert final_bundle.index("$externalHandoff = Invoke-ExternalHandoff") < final_bundle.index(
        'Add-Item -Name "final_external_handoff_zip"'
    )
