# SPDX-License-Identifier: Apache-2.0

from typing import Any

from pydantic import BaseModel, Field

from dream.audit.models import AuditRecord


class IntakeDocument(BaseModel):
    document_id: str
    team_id: str
    title: str
    document_type: str
    original_path: str
    stored_path: str
    source_hash: str | None = None
    promoted_path: str | None = None
    status: str = "uploaded"
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)


class SourceSpan(BaseModel):
    start_line: int | None = None
    end_line: int | None = None


class ParsedSection(BaseModel):
    section_id: str
    heading: str
    level: int
    text: str
    concepts: list[str] = Field(default_factory=list)
    source_reference: str | None = None
    source_span: SourceSpan | None = None
    section_hash: str | None = None


class ExtractedConcept(BaseModel):
    concept: str
    source_sections: list[str] = Field(default_factory=list)
    confidence: float = 0.7


class KnowledgeDraft(BaseModel):
    draft_id: str
    document_id: str
    team_id: str
    title: str
    target_doc_type: str
    source_hash: str | None = None
    app: str | None = None
    component: str | None = None
    sections: list[ParsedSection] = Field(default_factory=list)
    concepts: list[ExtractedConcept] = Field(default_factory=list)
    normalized_markdown: str
    review_status: str = "pending_review"
    reviewer: str | None = None
    review_notes: str | None = None
    promoted_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    json_path: str | None = None
    markdown_path: str | None = None


class DraftMetadataSnapshot(BaseModel):
    title: str
    target_doc_type: str
    app: str | None = None
    component: str | None = None
    concepts: list[str] = Field(default_factory=list)
    review_status: str
    promoted_path: str | None = None


class DraftMetadataDiff(BaseModel):
    field: str
    before: Any | None = None
    after: Any | None = None


class DraftReviewEvent(BaseModel):
    event_id: str
    event_type: str
    draft_id: str
    document_id: str
    team_id: str
    created_at: str
    reviewer: str | None = None
    notes: str | None = None
    previous_status: str
    new_status: str
    audit_run_id: str
    metadata_snapshot: DraftMetadataSnapshot
    metadata_diff: list[DraftMetadataDiff] = Field(default_factory=list)
    source_hash: str | None = None
    section_hashes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    status: str
    reviewer: str | None = None
    notes: str | None = None


class DraftMetadataUpdate(BaseModel):
    title: str | None = None
    target_doc_type: str | None = None
    app: str | None = None
    component: str | None = None
    concepts: list[str] | None = None
    reviewer: str | None = None
    notes: str | None = None


class PromotionResult(BaseModel):
    document_id: str
    draft_id: str
    promoted_path: str
    status: str
    warnings: list[str] = Field(default_factory=list)


class SectionMatchProof(BaseModel):
    section_id: str
    heading: str
    source_reference: str | None = None
    source_span: SourceSpan | None = None
    section_hash: str | None = None


class SourceMatchProof(BaseModel):
    retrieved_source_path: str
    matched_path: str
    matched_label: str
    document_id: str
    draft_id: str | None = None
    source_hash: str | None = None
    source_hash_verified: bool | None = None
    section_proofs: list[SectionMatchProof] = Field(default_factory=list)


class DownstreamUsage(BaseModel):
    audit_record: AuditRecord
    matched_source_paths: list[str] = Field(default_factory=list)
    match_reason: str
    detail_route: str | None = None
    match_proofs: list[SourceMatchProof] = Field(default_factory=list)


class IntakeDocumentDetail(BaseModel):
    document: IntakeDocument
    draft: KnowledgeDraft | None = None
    raw_text: str
    raw_text_truncated: bool = False
    raw_size_bytes: int = 0
    raw_text_available: bool = True
    raw_text_warning: str | None = None
    source_hash_verified: bool | None = None
    audit_events: list[AuditRecord] = Field(default_factory=list)
    review_events: list[DraftReviewEvent] = Field(default_factory=list)
    downstream_events: list[AuditRecord] = Field(default_factory=list)
    downstream_usages: list[DownstreamUsage] = Field(default_factory=list)
