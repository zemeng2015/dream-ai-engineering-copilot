# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.memory.models import MemoryIntakeProof


class RetrievalStep(BaseModel):
    step_name: str
    query: str
    provider: str
    candidates_found: int
    selected_count: int
    notes: list[str] = Field(default_factory=list)


class EvidenceCandidate(BaseModel):
    evidence_id: str
    source_type: str
    title: str
    source_path: str
    excerpt: str
    score: float
    reason: str
    selected: bool = False
    excluded_reason: str | None = None
    concepts: list[str] = Field(default_factory=list)
    authority_status: str = "unknown"


class MemoryClaimReference(BaseModel):
    claim_id: str
    status: str
    entity: str
    relation: str
    value: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    intake_proofs: list[MemoryIntakeProof] = Field(default_factory=list)
    reason: str = ""


class GraphPathReference(BaseModel):
    query: str
    path: str
    source_paths: list[str] = Field(default_factory=list)


class RetrievalTrail(BaseModel):
    trail_id: str
    run_id: str | None = None
    case_id: str | None = None
    review_id: str | None = None
    team_id: str
    repo_name: str | None = None
    raw_query: str
    detected_concepts: list[str] = Field(default_factory=list)
    retrieval_steps: list[RetrievalStep] = Field(default_factory=list)
    candidate_evidence: list[EvidenceCandidate] = Field(default_factory=list)
    selected_evidence: list[EvidenceCandidate] = Field(default_factory=list)
    excluded_evidence: list[EvidenceCandidate] = Field(default_factory=list)
    ranking_reasons: list[str] = Field(default_factory=list)
    graph_expansion_paths: list[GraphPathReference] = Field(default_factory=list)
    memory_claims_considered: list[MemoryClaimReference] = Field(default_factory=list)
    memory_claims_used: list[MemoryClaimReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_context_summary: str
    json_path: str | None = None
    markdown_path: str | None = None


class ContextPack(BaseModel):
    context_pack_id: str
    case_id: str | None = None
    run_id: str | None = None
    review_id: str | None = None
    team_id: str
    repo_name: str | None = None
    user_request: str
    selected_docs: list[EvidenceCandidate] = Field(default_factory=list)
    selected_code: list[EvidenceCandidate] = Field(default_factory=list)
    selected_tests: list[EvidenceCandidate] = Field(default_factory=list)
    selected_incidents: list[EvidenceCandidate] = Field(default_factory=list)
    selected_historical_jira: list[EvidenceCandidate] = Field(default_factory=list)
    selected_historical_pr: list[EvidenceCandidate] = Field(default_factory=list)
    selected_memory_claims: list[MemoryClaimReference] = Field(default_factory=list)
    candidate_memory_claims: list[MemoryClaimReference] = Field(default_factory=list)
    excluded_evidence: list[EvidenceCandidate] = Field(default_factory=list)
    graph_paths: list[GraphPathReference] = Field(default_factory=list)
    deterministic_size_budget: int = 20
    selected_evidence_count: int
    warnings: list[str] = Field(default_factory=list)
    json_path: str | None = None
    markdown_path: str | None = None


class PromptPreview(BaseModel):
    preview_id: str
    case_id: str | None = None
    run_id: str | None = None
    target: str
    provider_mode: str
    prompt_text: str
    evidence_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    json_path: str | None = None
    markdown_path: str | None = None


class EvidenceCard(BaseModel):
    card_id: str
    title: str
    source_path: str
    source_type: str
    short_abstract: str
    structured_overview: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    related_sources: list[str] = Field(default_factory=list)
    authority_status: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class MemoryMapReport(BaseModel):
    report_id: str
    team_id: str
    repo_name: str | None = None
    top_concepts: list[str] = Field(default_factory=list)
    most_connected_sources: list[str] = Field(default_factory=list)
    important_paths: list[str] = Field(default_factory=list)
    missing_test_links: list[str] = Field(default_factory=list)
    approved_memory_claims: int = 0
    candidate_memory_claims: int = 0
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    json_path: str | None = None
    markdown_path: str | None = None
