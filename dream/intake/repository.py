# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.paths import display_path, resolve_artifact_path
from dream.intake.models import IntakeDocument, KnowledgeDraft


class IntakeRepository:
    def save_document(self, document: IntakeDocument) -> IntakeDocument:
        path = self.document_path(document.document_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        return document

    def get_document(self, document_id: str) -> IntakeDocument:
        return IntakeDocument.model_validate_json(
            self.document_path(document_id).read_text(encoding="utf-8")
        )

    def list_documents(self) -> list[IntakeDocument]:
        base = resolve_artifact_path("intake/documents")
        if not base.exists():
            return []
        return [
            IntakeDocument.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(base.glob("*.json"))
        ]

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

    def document_path(self, document_id: str) -> Path:
        return resolve_artifact_path(
            Path("intake/documents") / f"{self._safe_name(document_id)}.json"
        )

    @staticmethod
    def upload_path(document_id: str, suffix: str) -> Path:
        base = resolve_artifact_path("intake/uploads")
        base.mkdir(parents=True, exist_ok=True)
        return base / f"{IntakeRepository._safe_name(document_id)}{suffix}"

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
