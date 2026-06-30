# SPDX-License-Identifier: Apache-2.0

from dream.intake import KnowledgeIntakeService, ReviewDecision


def test_knowledge_intake_parse_review_and_promote(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    sample = tmp_path / "status-runbook.md"
    sample.write_text(
        """# Status Stuck Running Runbook

## Symptoms
Execution status remains RUNNING after processor completion.

## Resolution
Check StatusTracker persistence and operator retry notes.
""",
        encoding="utf-8",
    )
    service = KnowledgeIntakeService(knowledge_root=tmp_path / "knowledge_packs")

    document = service.upload_local_file(
        team_id="demo_team",
        file_path=sample,
        document_type="runbooks",
    )
    draft = service.parse_document(document.document_id)
    reviewed = service.review_draft(
        draft.draft_id,
        ReviewDecision(status="approved", reviewer="qa", notes="Synthetic sample approved."),
    )
    promoted = service.promote_draft(reviewed.draft_id)

    assert document.status == "uploaded"
    assert draft.sections
    assert "execution status" in draft.normalized_markdown.lower()
    assert reviewed.review_status == "approved"
    assert promoted.status == "promoted"
    assert (tmp_path / "knowledge_packs" / "demo_team" / "docs" / "runbooks").exists()
