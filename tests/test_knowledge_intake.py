# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.intake import DraftMetadataUpdate, KnowledgeIntakeService, ReviewDecision


def test_knowledge_intake_parse_review_and_promote(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
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
    service = KnowledgeIntakeService(
        audit_logger=AuditLogger(repository=audit_repository),
        knowledge_root=tmp_path / "knowledge_packs",
    )

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
    service.audit_logger.log_generation(
        run_id="jira-draft-case-demo",
        use_case="jira_draft",
        team_id="demo_team",
        input_payload={"document_id": document.document_id},
        retrieved_source_paths=[promoted.promoted_path],
        model_provider="deterministic",
        model_name="requirement-case-jira-v1",
        output_path="artifacts/requirement-cases/case-demo/jira-draft.md",
        status="success",
        warnings=[],
    )
    detail = service.get_document_detail(document.document_id)

    assert document.status == "uploaded"
    assert document.source_hash and document.source_hash.startswith("sha256:")
    assert draft.sections
    assert draft.source_hash == document.source_hash
    assert all(section.section_hash for section in draft.sections)
    assert all(section.source_span for section in draft.sections)
    assert "execution status" in draft.normalized_markdown.lower()
    assert "source_hash: sha256:" in draft.normalized_markdown
    assert "Section hash: `sha256:" in draft.normalized_markdown
    assert reviewed.review_status == "approved"
    assert promoted.status == "promoted"
    promoted_markdown = Path(promoted.promoted_path).read_text(encoding="utf-8")
    assert "source_hash: sha256:" in promoted_markdown
    assert "Source span: `L" in promoted_markdown
    assert (
        service.repository.get_document(document.document_id).promoted_path
        == promoted.promoted_path
    )
    assert detail.document.document_id == document.document_id
    assert detail.draft is not None
    assert detail.draft.review_status == "promoted"
    assert "Execution status remains RUNNING" in detail.raw_text
    assert detail.raw_size_bytes > 0
    assert detail.source_hash_verified is True
    assert detail.draft.sections[0].source_span is not None
    assert detail.draft.sections[0].section_hash.startswith("sha256:")
    review_events = service.repository.list_review_events(draft.draft_id)
    assert {event.event_type for event in review_events} == {
        "review_decision",
        "promotion",
    }
    assert detail.review_events == review_events
    decision_event = next(
        event for event in review_events if event.event_type == "review_decision"
    )
    assert decision_event.audit_run_id == f"intake-review-{draft.draft_id}"
    assert decision_event.reviewer == "qa"
    assert decision_event.previous_status == "pending_review"
    assert decision_event.new_status == "approved"
    assert any(
        diff.field == "review_status"
        and diff.before == "pending_review"
        and diff.after == "approved"
        for diff in decision_event.metadata_diff
    )
    assert decision_event.source_hash == document.source_hash
    assert decision_event.section_hashes
    assert (tmp_path / "knowledge_packs" / "demo_team" / "docs" / "runbooks").exists()
    use_cases = {record.use_case for record in audit_repository.list_audit_records()}
    assert {
        "knowledge_intake_upload",
        "knowledge_intake_parse",
        "knowledge_intake_review",
        "knowledge_intake_promote",
    }.issubset(use_cases)
    assert {
        "knowledge_intake_upload",
        "knowledge_intake_parse",
        "knowledge_intake_review",
        "knowledge_intake_promote",
    }.issubset({record.use_case for record in detail.audit_events})
    assert "jira_draft" not in {record.use_case for record in detail.audit_events}
    assert "jira_draft" in {record.use_case for record in detail.downstream_events}
    assert detail.downstream_usages[0].audit_record.use_case == "jira_draft"
    assert detail.downstream_usages[0].matched_source_paths == [promoted.promoted_path]
    assert (
        detail.downstream_usages[0].match_reason
        == "Retrieved source matched promoted structured Markdown."
    )
    assert detail.downstream_usages[0].detail_route == "/audit/jira-draft-case-demo"
    proof = detail.downstream_usages[0].match_proofs[0]
    assert proof.retrieved_source_path == promoted.promoted_path
    assert proof.matched_path == promoted.promoted_path
    assert proof.matched_label == "promoted structured Markdown"
    assert proof.document_id == document.document_id
    assert proof.draft_id == draft.draft_id
    assert proof.source_hash == document.source_hash
    assert proof.source_hash_verified is True
    assert proof.section_proofs
    assert proof.section_proofs[0].source_span is not None
    assert proof.section_proofs[0].section_hash.startswith("sha256:")


def test_knowledge_intake_strips_utf8_bom(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    sample = tmp_path / "bom-runbook.md"
    sample.write_text(
        "\ufeff# BOM Runbook\n\n## Status\nExecution status is visible.",
        encoding="utf-8",
    )
    service = KnowledgeIntakeService(
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
        knowledge_root=tmp_path / "knowledge_packs",
    )

    document = service.upload_local_file(
        team_id="demo_team",
        file_path=sample,
        document_type="runbooks",
    )
    draft = service.parse_document(document.document_id)

    assert all("\ufeff" not in section.heading for section in draft.sections)
    assert "\ufeff" not in draft.normalized_markdown


def test_knowledge_intake_accepts_browser_uploaded_content(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    service = KnowledgeIntakeService(
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
        knowledge_root=tmp_path / "knowledge_packs",
    )

    document = service.upload_file_content(
        team_id="demo_team",
        filename="browser-status-runbook.md",
        content=(
            b"# Browser Status Runbook\n\n"
            b"## Recovery\n"
            b"Operators verify execution status before retry."
        ),
        document_type="runbooks",
    )
    draft = service.parse_document(document.document_id)

    assert document.original_path == "uploaded://browser-status-runbook.md"
    assert document.source_hash and document.source_hash.startswith("sha256:")
    assert document.stored_path.endswith(".md")
    assert draft.sections
    assert "execution status" in draft.normalized_markdown.lower()


def test_knowledge_intake_warns_on_duplicate_source_hash(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    service = KnowledgeIntakeService(
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
        knowledge_root=tmp_path / "knowledge_packs",
    )
    content = b"# Duplicate Runbook\n\n## Recovery\nRetry only after status is final."

    first = service.upload_file_content(
        team_id="demo_team",
        filename="duplicate-a.md",
        content=content,
        document_type="runbooks",
    )
    second = service.upload_file_content(
        team_id="demo_team",
        filename="duplicate-b.md",
        content=content,
        document_type="runbooks",
    )

    assert first.source_hash == second.source_hash
    assert second.warnings
    assert first.document_id in second.warnings[0]
    assert service.parse_document(second.document_id).warnings == second.warnings


def test_knowledge_intake_updates_metadata_before_promote(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    sample = tmp_path / "metadata-runbook.md"
    sample.write_text(
        "# Metadata Runbook\n\n## Coverage\nRetry coverage needs operator review.",
        encoding="utf-8",
    )
    service = KnowledgeIntakeService(
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
        knowledge_root=tmp_path / "knowledge_packs",
    )

    document = service.upload_local_file(
        team_id="demo_team",
        file_path=sample,
        document_type="runbooks",
    )
    draft = service.parse_document(document.document_id)
    updated = service.update_draft_metadata(
        draft.draft_id,
        DraftMetadataUpdate(
            title="Reviewed Metadata Intake",
            target_doc_type="testing",
            app="ForecastDemo",
            component="qa-review",
            concepts=["retry policy", "operator review"],
        ),
    )
    reviewed = service.review_draft(
        updated.draft_id,
        ReviewDecision(status="approved", reviewer="qa"),
    )
    promoted = service.promote_draft(reviewed.draft_id)
    promoted_path = tmp_path / "knowledge_packs" / "demo_team" / "docs" / "testing"

    assert updated.title == "Reviewed Metadata Intake"
    assert updated.target_doc_type == "testing"
    assert "component: qa-review" in updated.normalized_markdown
    assert "retry policy" in updated.normalized_markdown
    assert promoted_path.exists()
    assert promoted.promoted_path.endswith(".md")
    assert "reviewed-metadata-intake" in promoted.promoted_path
    assert "docs/testing" in promoted.promoted_path.replace("\\", "/")
    review_events = service.repository.list_review_events(draft.draft_id)
    metadata_event = next(
        event for event in review_events if event.event_type == "metadata_update"
    )
    assert metadata_event.audit_run_id == f"intake-metadata-{draft.draft_id}"
    assert {
        diff.field for diff in metadata_event.metadata_diff
    }.issuperset({"title", "target_doc_type", "component", "concepts"})
    assert metadata_event.metadata_snapshot.title == "Reviewed Metadata Intake"
    assert metadata_event.metadata_snapshot.target_doc_type == "testing"
