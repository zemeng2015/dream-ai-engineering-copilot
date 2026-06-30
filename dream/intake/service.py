# SPDX-License-Identifier: Apache-2.0

import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dream.core.paths import display_path, get_knowledge_packs_dir
from dream.intake.models import (
    ExtractedConcept,
    IntakeDocument,
    KnowledgeDraft,
    PromotionResult,
    ReviewDecision,
)
from dream.intake.parsers import IntakeParser
from dream.intake.repository import IntakeRepository


class KnowledgeIntakeService:
    def __init__(
        self,
        *,
        repository: IntakeRepository | None = None,
        parser: IntakeParser | None = None,
        knowledge_root: Path | None = None,
    ) -> None:
        self.repository = repository or IntakeRepository()
        self.parser = parser or IntakeParser()
        self.knowledge_root = knowledge_root or get_knowledge_packs_dir()

    def upload_local_file(
        self,
        *,
        team_id: str,
        file_path: str | Path,
        document_type: str,
        title: str | None = None,
    ) -> IntakeDocument:
        source = Path(file_path).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Intake file does not exist: {file_path}")
        now = datetime.now(UTC).isoformat()
        document_id = f"intake-{uuid4().hex[:12]}"
        target = self.repository.upload_path(document_id, source.suffix)
        shutil.copyfile(source, target)
        document = IntakeDocument(
            document_id=document_id,
            team_id=team_id,
            title=title or source.stem.replace("-", " ").replace("_", " ").title(),
            document_type=document_type,
            original_path=source.as_posix(),
            stored_path=display_path(target),
            created_at=now,
            updated_at=now,
        )
        return self.repository.save_document(document)

    def parse_document(self, document_id: str) -> KnowledgeDraft:
        document = self.repository.get_document(document_id)
        stored = Path(document.stored_path)
        path = stored if stored.is_absolute() else Path.cwd() / stored
        if not path.exists():
            from dream.core.paths import PROJECT_ROOT

            path = PROJECT_ROOT / document.stored_path
        sections = self.parser.parse(path)
        concepts = _concepts_from_sections(sections)
        markdown = _normalized_markdown(document, sections, concepts)
        draft = KnowledgeDraft(
            draft_id=f"draft-{document.document_id}",
            document_id=document.document_id,
            team_id=document.team_id,
            title=document.title,
            target_doc_type=document.document_type,
            sections=sections,
            concepts=concepts,
            normalized_markdown=markdown,
            warnings=[] if sections else ["No sections were parsed from this document."],
        )
        document.status = "parsed"
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        return self.repository.save_draft(draft)

    def review_draft(self, draft_id: str, decision: ReviewDecision) -> KnowledgeDraft:
        draft = self.repository.get_draft(draft_id)
        draft.review_status = decision.status
        draft.reviewer = decision.reviewer
        draft.review_notes = decision.notes
        document = self.repository.get_document(draft.document_id)
        document.status = decision.status
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        return self.repository.save_draft(draft)

    def promote_draft(self, draft_id: str) -> PromotionResult:
        draft = self.repository.get_draft(draft_id)
        if draft.review_status != "approved":
            raise ValueError("Only approved knowledge drafts can be promoted.")
        target_dir = self.knowledge_root / draft.team_id / "docs" / draft.target_doc_type
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{_safe_slug(draft.title)}-{draft.document_id}.md"
        target_path.write_text(draft.normalized_markdown, encoding="utf-8")
        draft.promoted_path = display_path(target_path)
        draft.review_status = "promoted"
        self.repository.save_draft(draft)
        document = self.repository.get_document(draft.document_id)
        document.status = "promoted"
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        return PromotionResult(
            document_id=draft.document_id,
            draft_id=draft.draft_id,
            promoted_path=display_path(target_path),
            status="promoted",
        )


def _concepts_from_sections(sections) -> list[ExtractedConcept]:
    counts: Counter[str] = Counter()
    section_ids: dict[str, list[str]] = {}
    for section in sections:
        for concept in section.concepts:
            counts[concept] += 1
            section_ids.setdefault(concept, []).append(section.section_id)
    return [
        ExtractedConcept(
            concept=concept,
            source_sections=section_ids[concept],
            confidence=min(0.95, 0.55 + count * 0.1),
        )
        for concept, count in counts.most_common(12)
    ]


def _normalized_markdown(
    document: IntakeDocument,
    sections,
    concepts: list[ExtractedConcept],
) -> str:
    concept_values = ", ".join(concept.concept for concept in concepts[:8])
    body = []
    for section in sections:
        heading = "#" * min(max(section.level, 2), 4)
        body.append(f"{heading} {section.heading}")
        body.append("")
        body.append(section.text or "_No body text parsed._")
        body.append("")
        body.append(f"Source reference: `{section.source_reference}`")
        body.append("")
    return f"""---
title: {document.title}
app: ForecastDemo
component: knowledge-intake
doc_type: {document.document_type}
concepts: [{concept_values}]
source: {document.original_path}
review_status: pending_review
---

# {document.title}

Imported through DREAM Knowledge Intake. Human review is required before using
this as authoritative context.

{chr(10).join(body).rstrip()}
"""


def _safe_slug(value: str) -> str:
    return (
        value.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace("/", "-")
        .replace("\\", "-")
    )[:80]
