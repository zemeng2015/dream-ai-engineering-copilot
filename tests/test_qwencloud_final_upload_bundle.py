# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_upload_bundle_refreshes_action_board_for_each_bundle() -> None:
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert '[string]$RepoName = "zemeng2015/dream-ai-engineering-copilot"' in final_bundle
    assert '[string]$RepoRef = "codex/champion-memory-loop"' in final_bundle
    assert "function Invoke-PowerShellProcess" in final_bundle
    assert "-ArgumentList $quotedArguments" in final_bundle
    assert "-ArgumentList $args" not in final_bundle
    assert "[switch]$SkipGitHubSecrets" in final_bundle
    assert "function Invoke-ActionBoard" in final_bundle
    assert "function Invoke-ExternalHandoff" in final_bundle
    assert "function Invoke-ReleaseConfigAudit" in final_bundle
    assert "function Invoke-VideoUploadStatus" in final_bundle
    assert 'Add-ExternalRequirement -Name "current_public_demo_video_ready"' in final_bundle
    assert 'Add-Item -Name "video_upload_status_json"' in final_bundle
    assert "releaseSummaryPackaging" in final_bundle
    assert "not_bundled_generate_after_zip_hash" in final_bundle
    assert "function Protect-ManifestText" in final_bundle
    assert "function Protect-BundledTextFile" in final_bundle
    assert "Get-PortableManifestPath -Path $dest" in final_bundle
    assert "portableRedactionApplied" in final_bundle
    assert '"scripts/qwencloud-final-action-board.ps1"' in final_bundle
    assert '"scripts/qwencloud-final-external-handoff.ps1"' in final_bundle
    assert '"-RepoName", $RepoName' in final_bundle
    assert 'if ($SkipGitHubSecrets) { $args += "-SkipGitHubSecrets" }' in final_bundle
    assert "$actionBoard = Invoke-ActionBoard" in final_bundle
    assert "$externalHandoff = Invoke-ExternalHandoff" in final_bundle
    assert "$releaseConfig = Invoke-ReleaseConfigAudit" in final_bundle
    assert 'Add-ExternalRequirement -Name "release_config_audit_ready"' in final_bundle
    assert 'Add-Item -Name "release_config_audit_markdown"' in final_bundle
    assert 'Add-Item -Name "release_config_audit_json"' in final_bundle
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
    assert 'Add-Item -Name "final_external_handoff_zip"' not in final_bundle
    assert "latest_seeded_demo_artifact_zip" not in final_bundle
    assert "latest_final_action_board_markdown" not in final_bundle
    assert "latest_final_action_board_json" not in final_bundle
    assert "latest_final_external_handoff_markdown" not in final_bundle
    assert "latest_final_external_handoff_json" not in final_bundle
    assert "latest_final_external_handoff_zip" not in final_bundle
    assert "latest_github_release_summary_markdown" not in final_bundle
    assert "latest_github_release_summary_json" not in final_bundle

    assert final_bundle.index("function Invoke-ActionBoard") < final_bundle.index(
        "$actionBoard = Invoke-ActionBoard"
    )
    assert final_bundle.index("$actionBoard = Invoke-ActionBoard") < final_bundle.index(
        "$externalHandoff = Invoke-ExternalHandoff"
    )
    assert final_bundle.index("$externalHandoff = Invoke-ExternalHandoff") < final_bundle.index(
        'Add-Item -Name "final_action_board_json"'
    )
