# SPDX-License-Identifier: Apache-2.0

import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.audit.models import AuditRecord
from dream.config import resolve_config
from dream.core.errors import DlpBlockedError
from dream.core.paths import display_path, get_knowledge_packs_dir
from dream.dlp import DefaultDlpEngine
from dream.intake.models import (
    DownstreamUsage,
    DraftMetadataDiff,
    DraftMetadataSnapshot,
    DraftMetadataUpdate,
    DraftReviewEvent,
    ExtractedConcept,
    IntakeDocument,
    IntakeDocumentDetail,
    KnowledgeDraft,
    PromotionResult,
    ReviewDecision,
    SectionMatchProof,
    SourceMatchProof,
)
from dream.intake.parsers import IntakeParser
from dream.intake.repository import IntakeRepository
from dream.knowledge.pack_loader import KnowledgePackLoader

RAW_TEXT_PREVIEW_LIMIT = 80_000


@dataclass(frozen=True)
class _SourceCandidatePath:
    label: str
    path: str


class KnowledgeIntakeService:
    def __init__(
        self,
        *,
        repository: IntakeRepository | None = None,
        parser: IntakeParser | None = None,
        knowledge_root: Path | None = None,
        audit_logger: AuditLogger | None = None,
        dlp_engine: DefaultDlpEngine | None = None,
    ) -> None:
        self.repository = repository or IntakeRepository()
        self.parser = parser or IntakeParser()
        self.knowledge_root = knowledge_root or get_knowledge_packs_dir()
        self.audit_logger = audit_logger or AuditLogger()
        self.dlp_engine = dlp_engine or DefaultDlpEngine()

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
        source_bytes = source.read_bytes()
        source_hash = _source_hash(source_bytes)
        warnings = _duplicate_warnings(
            self.repository.find_by_source_hash(team_id=team_id, source_hash=source_hash)
        )
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
            source_hash=source_hash,
            created_at=now,
            updated_at=now,
            warnings=warnings,
        )
        saved = self.repository.save_document(document)
        self.audit_logger.log_generation(
            run_id=f"intake-upload-{document.document_id}",
            use_case="knowledge_intake_upload",
            team_id=team_id,
            input_payload={
                "document_id": document.document_id,
                "file_path": source.as_posix(),
                "document_type": document_type,
                "source_hash": source_hash,
            },
            retrieved_source_paths=[source.as_posix()],
            model_provider="local",
            model_name="knowledge-intake-upload-v1",
            output_path=document.stored_path,
            status=document.status,
            warnings=document.warnings,
        )
        return saved

    def upload_file_content(
        self,
        *,
        team_id: str,
        filename: str,
        content: bytes,
        document_type: str,
        title: str | None = None,
    ) -> IntakeDocument:
        source_name = Path(filename or "uploaded-source").name
        source_hash = _source_hash(content)
        warnings = _duplicate_warnings(
            self.repository.find_by_source_hash(team_id=team_id, source_hash=source_hash)
        )
        now = datetime.now(UTC).isoformat()
        document_id = f"intake-{uuid4().hex[:12]}"
        target = self.repository.upload_path(document_id, Path(source_name).suffix)
        target.write_bytes(content)
        original_path = f"uploaded://{source_name}"
        document = IntakeDocument(
            document_id=document_id,
            team_id=team_id,
            title=title or _title_from_source_name(source_name),
            document_type=document_type,
            original_path=original_path,
            stored_path=display_path(target),
            source_hash=source_hash,
            created_at=now,
            updated_at=now,
            warnings=warnings,
        )
        saved = self.repository.save_document(document)
        self.audit_logger.log_generation(
            run_id=f"intake-upload-{document.document_id}",
            use_case="knowledge_intake_upload",
            team_id=team_id,
            input_payload={
                "document_id": document.document_id,
                "filename": source_name,
                "import_method": "browser_upload",
                "document_type": document_type,
                "size_bytes": len(content),
                "source_hash": source_hash,
            },
            retrieved_source_paths=[original_path],
            model_provider="local",
            model_name="knowledge-intake-upload-v1",
            output_path=document.stored_path,
            status=document.status,
            warnings=document.warnings,
        )
        return saved

    def parse_document(self, document_id: str) -> KnowledgeDraft:
        document = self.repository.get_document(document_id)
        stored = Path(document.stored_path)
        path = stored if stored.is_absolute() else Path.cwd() / stored
        if not path.exists():
            from dream.core.paths import PROJECT_ROOT

            path = PROJECT_ROOT / document.stored_path
        classification = (
            "internal" if resolve_config().mode == "private-extension" else "public_demo"
        )
        try:
            inspection = self.dlp_engine.enforce(
                self.parser.extract_text(path),
                stage="pre_index",
                team_id=document.team_id,
                resource_id=document.document_id,
                classification=classification,
            )
        except DlpBlockedError:
            document.status = "quarantined"
            document.updated_at = datetime.now(UTC).isoformat()
            document.warnings = list(
                dict.fromkeys([*document.warnings, "DLP blocked source content from parsing."])
            )
            self.repository.save_document(document)
            self.audit_logger.log_generation(
                run_id=f"intake-dlp-block-{document.document_id}",
                use_case="knowledge_intake_dlp",
                team_id=document.team_id,
                input_payload={"document_id": document.document_id},
                retrieved_source_paths=[document.stored_path],
                model_provider="deterministic",
                model_name=self.dlp_engine.policy_version,
                output_path="none",
                status="quarantined",
                warnings=document.warnings,
            )
            raise
        sections = self.parser.parse_text(
            inspection.sanitized_text,
            source_path=path.as_posix(),
        )
        concepts = _concepts_from_sections(sections)
        app, component = _infer_app_component(document, sections, concepts)
        draft = KnowledgeDraft(
            draft_id=f"draft-{document.document_id}",
            document_id=document.document_id,
            team_id=document.team_id,
            title=document.title,
            target_doc_type=document.document_type,
            source_hash=document.source_hash,
            app=app,
            component=component,
            sections=sections,
            concepts=concepts,
            normalized_markdown="",
            warnings=[
                *(document.warnings or []),
                *(
                    [
                        f"DLP {inspection.evidence.policy_version} redacted "
                        f"{inspection.evidence.redaction_count} finding(s) before parsing."
                    ]
                    if inspection.evidence.redaction_count
                    else []
                ),
                *([] if sections else ["No sections were parsed from this document."]),
            ],
        )
        draft.normalized_markdown = _normalized_markdown(document, draft)
        document.status = "parsed"
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        saved = self.repository.save_draft(draft)
        self.audit_logger.log_generation(
            run_id=f"intake-parse-{document.document_id}",
            use_case="knowledge_intake_parse",
            team_id=document.team_id,
            input_payload={
                "document_id": document.document_id,
                "source_hash": document.source_hash,
                "section_hashes": [section.section_hash for section in sections],
            },
            retrieved_source_paths=[document.stored_path],
            model_provider="deterministic",
            model_name="knowledge-intake-parser-v1",
            output_path=saved.markdown_path or "artifact:intake/drafts",
            status=document.status,
            warnings=saved.warnings,
        )
        return saved

    def review_draft(self, draft_id: str, decision: ReviewDecision) -> KnowledgeDraft:
        draft = self.repository.get_draft(draft_id)
        previous_snapshot = _draft_metadata_snapshot(draft)
        draft.review_status = decision.status
        draft.reviewer = decision.reviewer
        draft.review_notes = decision.notes
        document = self.repository.get_document(draft.document_id)
        document.status = decision.status
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        draft.normalized_markdown = _normalized_markdown(document, draft)
        saved = self.repository.save_draft(draft)
        audit_run_id = f"intake-review-{draft.draft_id}"
        self.audit_logger.log_generation(
            run_id=audit_run_id,
            use_case="knowledge_intake_review",
            team_id=draft.team_id,
            input_payload={
                "draft_id": draft_id,
                "status": decision.status,
                "reviewer": decision.reviewer,
                "notes": decision.notes,
            },
            retrieved_source_paths=[document.stored_path],
            model_provider="human",
            model_name="knowledge-intake-review-v1",
            output_path=saved.json_path or "artifact:intake/drafts",
            status=decision.status,
            warnings=saved.warnings,
        )
        self.repository.save_review_event(
            _draft_review_event(
                event_type="review_decision",
                draft=saved,
                previous_snapshot=previous_snapshot,
                reviewer=decision.reviewer,
                notes=decision.notes,
                audit_run_id=audit_run_id,
            )
        )
        return saved

    def update_draft_metadata(
        self,
        draft_id: str,
        update: DraftMetadataUpdate,
    ) -> KnowledgeDraft:
        draft = self.repository.get_draft(draft_id)
        if draft.review_status == "promoted":
            raise ValueError("Promoted knowledge drafts cannot be edited.")
        previous_snapshot = _draft_metadata_snapshot(draft)
        document = self.repository.get_document(draft.document_id)
        title = _clean_optional(update.title) or draft.title
        target_doc_type = (
            self._normalize_document_type(draft.team_id, update.target_doc_type)
            if update.target_doc_type is not None
            else draft.target_doc_type
        )
        concepts = (
            _concepts_from_values(update.concepts, draft.sections)
            if update.concepts is not None
            else draft.concepts
        )
        app, component = _infer_app_component(document, draft.sections, concepts)
        draft = draft.model_copy(
            update={
                "title": title,
                "target_doc_type": target_doc_type,
                "app": _clean_optional(update.app) or draft.app or app,
                "component": _clean_optional(update.component) or draft.component or component,
                "concepts": concepts,
            }
        )
        document.title = draft.title
        document.document_type = draft.target_doc_type
        document.updated_at = datetime.now(UTC).isoformat()
        draft.normalized_markdown = _normalized_markdown(document, draft)
        self.repository.save_document(document)
        saved = self.repository.save_draft(draft)
        audit_run_id = f"intake-metadata-{draft.draft_id}"
        self.audit_logger.log_generation(
            run_id=audit_run_id,
            use_case="knowledge_intake_metadata_update",
            team_id=draft.team_id,
            input_payload={
                "draft_id": draft.draft_id,
                "document_id": draft.document_id,
                "title": draft.title,
                "target_doc_type": draft.target_doc_type,
                "app": draft.app,
                "component": draft.component,
                "concepts": [concept.concept for concept in draft.concepts],
            },
            retrieved_source_paths=[document.stored_path],
            model_provider="human",
            model_name="knowledge-intake-metadata-v1",
            output_path=saved.markdown_path or "artifact:intake/drafts",
            status=saved.review_status,
            warnings=saved.warnings,
        )
        self.repository.save_review_event(
            _draft_review_event(
                event_type="metadata_update",
                draft=saved,
                previous_snapshot=previous_snapshot,
                reviewer=update.reviewer,
                notes=update.notes,
                audit_run_id=audit_run_id,
            )
        )
        return saved

    def promote_draft(self, draft_id: str) -> PromotionResult:
        draft = self.repository.get_draft(draft_id)
        if draft.review_status != "approved":
            raise ValueError("Only approved knowledge drafts can be promoted.")
        previous_snapshot = _draft_metadata_snapshot(draft)
        target_doc_type = self._normalize_document_type(draft.team_id, draft.target_doc_type)
        draft.target_doc_type = target_doc_type
        target_dir = self.knowledge_root / draft.team_id / "docs" / draft.target_doc_type
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{_safe_slug(draft.title)}-{draft.document_id}.md"
        draft.review_status = "promoted"
        draft.promoted_path = display_path(target_path)
        document = self.repository.get_document(draft.document_id)
        document.document_type = draft.target_doc_type
        draft.normalized_markdown = _normalized_markdown(document, draft)
        target_path.write_text(draft.normalized_markdown, encoding="utf-8")
        self.repository.save_draft(draft)
        document.status = "promoted"
        document.promoted_path = display_path(target_path)
        document.updated_at = datetime.now(UTC).isoformat()
        self.repository.save_document(document)
        result = PromotionResult(
            document_id=draft.document_id,
            draft_id=draft.draft_id,
            promoted_path=display_path(target_path),
            status="promoted",
        )
        audit_run_id = f"intake-promote-{draft.draft_id}"
        self.audit_logger.log_generation(
            run_id=audit_run_id,
            use_case="knowledge_intake_promote",
            team_id=draft.team_id,
            input_payload={"draft_id": draft_id, "document_id": draft.document_id},
            retrieved_source_paths=[document.stored_path],
            model_provider="deterministic",
            model_name="knowledge-pack-promotion-v1",
            output_path=result.promoted_path,
            status=result.status,
            warnings=result.warnings,
        )
        self.repository.save_review_event(
            _draft_review_event(
                event_type="promotion",
                draft=draft,
                previous_snapshot=previous_snapshot,
                reviewer=draft.reviewer,
                notes="Promoted approved draft into knowledge pack.",
                audit_run_id=audit_run_id,
            )
        )
        return result

    def get_document_detail(self, document_id: str) -> IntakeDocumentDetail:
        document = self.repository.get_document(document_id)
        draft = self._get_draft_or_none(f"draft-{document.document_id}")
        raw = self._read_raw_text(document)
        audit_records = self.audit_logger.repository.list_audit_records()
        audit_events = [
            record
            for record in audit_records
            if _audit_record_matches_document(
                record.run_id,
                document.document_id,
                draft.draft_id if draft else f"draft-{document.document_id}",
            )
        ]
        source_candidates = _source_candidate_paths(document, draft)
        source_hash_verified = (
            raw["source_hash_verified"] if isinstance(raw["source_hash_verified"], bool) else None
        )
        downstream_usages = [
            usage
            for record in audit_records
            if record.team_id == document.team_id and record not in audit_events
            for usage in [
                _downstream_usage_from_record(
                    record,
                    source_candidates,
                    document=document,
                    draft=draft,
                    source_hash_verified=source_hash_verified,
                )
            ]
            if usage is not None
        ]
        return IntakeDocumentDetail(
            document=document,
            draft=draft,
            raw_text=raw["text"],
            raw_text_truncated=raw["truncated"],
            raw_size_bytes=raw["size_bytes"],
            raw_text_available=raw["available"],
            raw_text_warning=raw["warning"],
            source_hash_verified=raw["source_hash_verified"],
            audit_events=audit_events,
            review_events=(self.repository.list_review_events(draft.draft_id) if draft else []),
            downstream_events=[usage.audit_record for usage in downstream_usages],
            downstream_usages=downstream_usages,
        )

    def _get_draft_or_none(self, draft_id: str) -> KnowledgeDraft | None:
        try:
            return self.repository.get_draft(draft_id)
        except OSError:
            return None

    def _read_raw_text(self, document: IntakeDocument) -> dict[str, object]:
        path = _resolve_stored_path(document.stored_path)
        content = path.read_bytes()
        size_bytes = len(content)
        source_hash_verified = (
            _source_hash(content) == document.source_hash if document.source_hash else None
        )
        if path.suffix.lower() == ".docx":
            return {
                "text": "",
                "truncated": False,
                "size_bytes": size_bytes,
                "available": False,
                "warning": "Raw DOCX preview is not exposed; use parsed sections for text review.",
                "source_hash_verified": source_hash_verified,
            }
        text = content.decode("utf-8-sig", errors="replace")
        truncated = len(text) > RAW_TEXT_PREVIEW_LIMIT
        return {
            "text": text[:RAW_TEXT_PREVIEW_LIMIT],
            "truncated": truncated,
            "size_bytes": size_bytes,
            "available": True,
            "warning": "Raw source preview was truncated." if truncated else None,
            "source_hash_verified": source_hash_verified,
        }

    def _normalize_document_type(self, team_id: str, document_type: str | None) -> str:
        normalized = _normalize_document_type_value(document_type)
        valid_types = self._valid_document_types(team_id)
        if valid_types and normalized not in valid_types:
            valid = ", ".join(sorted(valid_types))
            raise ValueError(f"document_type must match team.yaml document_paths: {valid}")
        return normalized

    def _valid_document_types(self, team_id: str) -> set[str]:
        try:
            pack = KnowledgePackLoader(packs_dir=self.knowledge_root).load(team_id)
        except Exception:  # noqa: BLE001
            return set()
        return {
            Path(document_path).name
            for document_path in pack.document_paths
            if Path(document_path).parts[:1] == ("docs",)
        }


def _draft_review_event(
    *,
    event_type: str,
    draft: KnowledgeDraft,
    previous_snapshot: DraftMetadataSnapshot,
    reviewer: str | None,
    notes: str | None,
    audit_run_id: str,
) -> DraftReviewEvent:
    now = datetime.now(UTC)
    snapshot = _draft_metadata_snapshot(draft)
    return DraftReviewEvent(
        event_id=f"{event_type}-{draft.draft_id}-{now.strftime('%Y%m%d%H%M%S%f')}",
        event_type=event_type,
        draft_id=draft.draft_id,
        document_id=draft.document_id,
        team_id=draft.team_id,
        created_at=now.isoformat(),
        reviewer=reviewer,
        notes=notes,
        previous_status=previous_snapshot.review_status,
        new_status=snapshot.review_status,
        audit_run_id=audit_run_id,
        metadata_snapshot=snapshot,
        metadata_diff=_metadata_diff(previous_snapshot, snapshot),
        source_hash=draft.source_hash,
        section_hashes=[section.section_hash for section in draft.sections if section.section_hash],
        warnings=draft.warnings,
    )


def _draft_metadata_snapshot(draft: KnowledgeDraft) -> DraftMetadataSnapshot:
    return DraftMetadataSnapshot(
        title=draft.title,
        target_doc_type=draft.target_doc_type,
        app=draft.app,
        component=draft.component,
        concepts=[concept.concept for concept in draft.concepts],
        review_status=draft.review_status,
        promoted_path=draft.promoted_path,
    )


def _metadata_diff(
    before: DraftMetadataSnapshot,
    after: DraftMetadataSnapshot,
) -> list[DraftMetadataDiff]:
    before_payload = before.model_dump()
    after_payload = after.model_dump()
    return [
        DraftMetadataDiff(
            field=field,
            before=before_payload.get(field),
            after=after_payload.get(field),
        )
        for field in before_payload
        if before_payload.get(field) != after_payload.get(field)
    ]


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


def _concepts_from_values(
    values: list[str] | None,
    sections,
) -> list[ExtractedConcept]:
    section_ids = [section.section_id for section in sections]
    concepts = []
    for value in values or []:
        normalized = " ".join(value.strip().split()).lower()
        if normalized and normalized not in [concept.concept for concept in concepts]:
            concepts.append(
                ExtractedConcept(
                    concept=normalized,
                    source_sections=section_ids,
                    confidence=0.8,
                )
            )
        if len(concepts) >= 12:
            break
    return concepts


def _normalized_markdown(document: IntakeDocument, draft: KnowledgeDraft) -> str:
    concept_values = ", ".join(concept.concept for concept in draft.concepts[:8])
    app = draft.app or "Unknown"
    component = draft.component or "knowledge-intake"
    body = []
    for section in draft.sections:
        heading = "#" * min(max(section.level, 2), 4)
        body.append(f"{heading} {section.heading}")
        body.append("")
        body.append(section.text or "_No body text parsed._")
        body.append("")
        body.append(f"Source reference: `{section.source_reference}`")
        if section.source_span:
            body.append(
                f"Source span: `L{section.source_span.start_line}-L{section.source_span.end_line}`"
            )
        if section.section_hash:
            body.append(f"Section hash: `{section.section_hash}`")
        body.append("")
    return f"""---
title: {draft.title}
app: {app}
component: {component}
doc_type: {draft.target_doc_type}
concepts: [{concept_values}]
source: {document.original_path}
intake_document_id: {document.document_id}
intake_draft_id: {draft.draft_id}
stored_path: {document.stored_path}
promoted_path: {draft.promoted_path or ""}
source_hash: {document.source_hash or "unknown"}
review_status: {draft.review_status}
---

# {draft.title}

Imported through DREAM Knowledge Intake. Human review is required before using
this as authoritative context.

{chr(10).join(body).rstrip()}
"""


def _infer_app_component(
    document: IntakeDocument,
    sections,
    concepts: list[ExtractedConcept],
) -> tuple[str, str]:
    text = " ".join(
        [
            document.title,
            document.document_type,
            document.original_path,
            " ".join(section.heading for section in sections),
            " ".join(section.text for section in sections),
            " ".join(concept.concept for concept in concepts),
        ]
    ).lower()
    app = "ForecastDemo"
    if "batch" in text:
        app = "BatchJobDemo"
    elif "output preview" in text or "preview" in text:
        app = "OutputPreviewDemo"

    if "output" in text or "reconciliation" in text or "artifact" in text:
        component = "output-collection"
    elif "status" in text or "running" in text or "execution" in text:
        component = "job-execution"
    elif "batch" in text or "scheduler" in text:
        component = "batch-job"
    else:
        component = "knowledge-intake"
    return app, component


def _safe_slug(value: str) -> str:
    return (value.lower().replace(" ", "-").replace("_", "-").replace("/", "-").replace("\\", "-"))[
        :80
    ]


def _title_from_source_name(source_name: str) -> str:
    return source_name.rsplit(".", maxsplit=1)[0].replace("-", " ").replace("_", " ").title()


def _resolve_stored_path(stored_path: str) -> Path:
    path = Path(stored_path)
    if path.exists():
        return path
    if not path.is_absolute():
        from dream.core.paths import PROJECT_ROOT

        project_path = PROJECT_ROOT / stored_path
        if project_path.exists():
            return project_path
    return path


def _audit_record_matches_document(
    run_id: str,
    document_id: str,
    draft_id: str,
) -> bool:
    return document_id in run_id or draft_id in run_id


def _source_candidate_paths(
    document: IntakeDocument,
    draft: KnowledgeDraft | None,
) -> dict[str, _SourceCandidatePath]:
    values = [
        ("original raw source", document.original_path),
        ("stored raw intake artifact", document.stored_path),
        ("promoted structured Markdown", document.promoted_path),
        ("promoted structured Markdown", draft.promoted_path if draft else None),
        ("draft normalized Markdown", draft.markdown_path if draft else None),
    ]
    return {
        _normalize_audit_path(value): _SourceCandidatePath(label=label, path=value)
        for label, value in values
        if value
    }


def _downstream_usage_from_record(
    record: AuditRecord,
    candidate_paths: dict[str, _SourceCandidatePath],
    *,
    document: IntakeDocument,
    draft: KnowledgeDraft | None,
    source_hash_verified: bool | None,
) -> DownstreamUsage | None:
    matched = _matched_source_paths(record, candidate_paths)
    if not matched:
        return None
    labels = sorted({candidate.label for candidate in matched.values()})
    return DownstreamUsage(
        audit_record=record,
        matched_source_paths=list(matched),
        match_reason=f"Retrieved source matched {', '.join(labels)}.",
        detail_route=_audit_detail_route(record),
        match_proofs=[
            _source_match_proof(
                retrieved_source_path=retrieved_source_path,
                candidate=candidate,
                document=document,
                draft=draft,
                source_hash_verified=source_hash_verified,
            )
            for retrieved_source_path, candidate in matched.items()
        ],
    )


def _matched_source_paths(
    record: AuditRecord,
    candidate_paths: dict[str, _SourceCandidatePath],
) -> dict[str, _SourceCandidatePath]:
    if not candidate_paths:
        return {}
    matches = {}
    for source_path in record.retrieved_source_paths:
        normalized = _normalize_audit_path(source_path)
        if normalized in candidate_paths:
            matches[source_path] = candidate_paths[normalized]
            continue
        for candidate, label in candidate_paths.items():
            if normalized.endswith(f"/{candidate}") or candidate.endswith(f"/{normalized}"):
                matches[source_path] = label
                break
    return matches


def _source_match_proof(
    *,
    retrieved_source_path: str,
    candidate: _SourceCandidatePath,
    document: IntakeDocument,
    draft: KnowledgeDraft | None,
    source_hash_verified: bool | None,
) -> SourceMatchProof:
    return SourceMatchProof(
        retrieved_source_path=retrieved_source_path,
        matched_path=candidate.path,
        matched_label=candidate.label,
        document_id=document.document_id,
        draft_id=draft.draft_id if draft else None,
        source_hash=document.source_hash,
        source_hash_verified=source_hash_verified,
        section_proofs=_section_match_proofs(draft),
    )


def _section_match_proofs(draft: KnowledgeDraft | None) -> list[SectionMatchProof]:
    if draft is None:
        return []
    return [
        SectionMatchProof(
            section_id=section.section_id,
            heading=section.heading,
            source_reference=section.source_reference,
            source_span=section.source_span,
            section_hash=section.section_hash,
        )
        for section in draft.sections
    ]


def _audit_detail_route(record: AuditRecord) -> str | None:
    if record.run_id.startswith("eval-"):
        return f"/audit/{record.run_id}"
    if record.case_id:
        return f"/audit/{record.case_id}"
    if record.run_id:
        return f"/audit/{record.run_id}"
    return None


def _normalize_audit_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip().lower()
    try:
        from dream.core.paths import PROJECT_ROOT

        project_root = PROJECT_ROOT.as_posix().lower().rstrip("/")
        if normalized.startswith(f"{project_root}/"):
            return normalized.removeprefix(f"{project_root}/")
    except OSError:
        pass
    return normalized


def _source_hash(content: bytes) -> str:
    return f"sha256:{sha256(content).hexdigest()}"


def _duplicate_warnings(existing: IntakeDocument | None) -> list[str]:
    if existing is None:
        return []
    return [
        "Duplicate source content matches existing intake document "
        f"{existing.document_id} ({existing.title})."
    ]


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_document_type_value(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("_", "-")
    aliases = {
        "incident": "incidents",
        "runbook": "runbooks",
        "test": "testing",
        "tests": "testing",
        "testing-doc": "testing",
        "domain-doc": "domain",
        "architecture-doc": "architecture",
    }
    return aliases.get(normalized, normalized)
