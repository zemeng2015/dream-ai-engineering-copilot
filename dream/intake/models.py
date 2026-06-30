# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class IntakeDocument(BaseModel):
    document_id: str
    team_id: str
    title: str
    document_type: str
    original_path: str
    stored_path: str
    status: str = "uploaded"
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)


class ParsedSection(BaseModel):
    section_id: str
    heading: str
    level: int
    text: str
    concepts: list[str] = Field(default_factory=list)
    source_reference: str | None = None


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


class ReviewDecision(BaseModel):
    status: str
    reviewer: str | None = None
    notes: str | None = None


class PromotionResult(BaseModel):
    document_id: str
    draft_id: str
    promoted_path: str
    status: str
    warnings: list[str] = Field(default_factory=list)
