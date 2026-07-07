# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.paths import display_path, resolve_artifact_path
from dream.intake.models import DraftReviewEvent, IntakeDocument, KnowledgeDraft


class IntakeRepository:
    def save_document(self, document: IntakeDocument) -> IntakeDocument:
        path = self.document_path(document.document_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        return document

    def get_document(self, document_id: str) -> IntakeDocument:
        document = IntakeDocument.model_validate_json(
            self.document_path(document_id).read_text(encoding="utf-8")
        )
        return self._with_promoted_path(document)

    def list_documents(self) -> list[IntakeDocument]:
        base = resolve_artifact_path("intake/documents")
        if not base.exists():
            return []
        return [
            self._with_promoted_path(
                IntakeDocument.model_validate_json(path.read_text(encoding="utf-8"))
            )
            for path in sorted(base.glob("*.json"))
        ]

    def find_by_source_hash(self, *, team_id: str, source_hash: str) -> IntakeDocument | None:
        for document in self.list_documents():
            if document.team_id == team_id and document.source_hash == source_hash:
                return document
        return None

    def save_draft(self, draft: KnowledgeDraft) -> KnowledgeDraft:
        base = resolve_artifact_path(Path("intake/drafts") / self._safe_name(draft.draft_id))
        base.mkdir(parents=True, exist_ok=True)
        json_path = base / "draft.json"
        markdown_path = base / "draft.md"
        updated = draft.model_copy(
            update={
                "json_path": display_path(json_path),
                "markdown_path": display_path(markdown_path),
            }
        )
        json_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(updated.normalized_markdown, encoding="utf-8")
        return updated

    def get_draft(self, draft_id: str) -> KnowledgeDraft:
        path = resolve_artifact_path(
            Path("intake/drafts") / self._safe_name(draft_id) / "draft.json"
        )
        return KnowledgeDraft.model_validate_json(path.read_text(encoding="utf-8"))

    def save_review_event(self, event: DraftReviewEvent) -> DraftReviewEvent:
        path = self.review_event_path(event.draft_id, event.event_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(event.model_dump_json(indent=2), encoding="utf-8")
        return event

    def list_review_events(self, draft_id: str) -> list[DraftReviewEvent]:
        base = resolve_artifact_path(
            Path("intake/drafts") / self._safe_name(draft_id) / "review-events"
        )
        if not base.exists():
            return []
        events = [
            DraftReviewEvent.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(base.glob("*.json"))
        ]
        return sorted(events, key=lambda event: event.created_at, reverse=True)

    def review_event_path(self, draft_id: str, event_id: str) -> Path:
        return resolve_artifact_path(
            Path("intake/drafts")
            / self._safe_name(draft_id)
            / "review-events"
            / f"{self._safe_name(event_id)}.json"
        )

    def document_path(self, document_id: str) -> Path:
        return resolve_artifact_path(
            Path("intake/documents") / f"{self._safe_name(document_id)}.json"
        )

    def _with_promoted_path(self, document: IntakeDocument) -> IntakeDocument:
        if document.promoted_path or document.status != "promoted":
            return document
        draft_path = resolve_artifact_path(
            Path("intake/drafts")
            / self._safe_name(f"draft-{document.document_id}")
            / "draft.json"
        )
        if not draft_path.exists():
            return document
        draft = KnowledgeDraft.model_validate_json(draft_path.read_text(encoding="utf-8"))
        return document.model_copy(update={"promoted_path": draft.promoted_path})

    @staticmethod
    def upload_path(document_id: str, suffix: str) -> Path:
        base = resolve_artifact_path("intake/uploads")
        base.mkdir(parents=True, exist_ok=True)
        return base / f"{IntakeRepository._safe_name(document_id)}{suffix}"

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
