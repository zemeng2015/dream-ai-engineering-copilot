# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    span_id: str
    source_id: str
    start_line: int | None = None
    end_line: int | None = None
    text_hash: str
    preview: str = ""


class SourceRecord(BaseModel):
    source_id: str
    source_type: str
    team_id: str
    repo_name: str | None = None
    path: str
    commit_sha: str | None = None
    content_hash: str
    indexed_at: str
    trust_level: str = "medium"
    acl_scope: str = "local"
    security_flags: list[str] = Field(default_factory=list)
    spans: list[SourceSpan] = Field(default_factory=list)


class MemoryEntity(BaseModel):
    entity_id: str
    entity_type: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)


class MemoryRelation(BaseModel):
    type: str
    object_entity_id: str | None = None
    value: str | None = None
    condition: str | None = None


class MemoryEvidenceSpan(BaseModel):
    source_id: str
    source_type: str
    path: str
    commit_sha: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    excerpt_hash: str
    span_id: str


class MemoryEvidence(BaseModel):
    source_ids: list[str] = Field(default_factory=list)
    spans: list[MemoryEvidenceSpan] = Field(default_factory=list)


class ExtractionInfo(BaseModel):
    method: str
    extractor_version: str
    model_name: str | None = None
    confidence: float


class GovernanceInfo(BaseModel):
    status: str = "candidate"
    risk_level: str = "low"
    reviewer: str | None = None
    reviewed_at: str | None = None
    rejection_reason: str | None = None


class TemporalInfo(BaseModel):
    valid_from: str | None = None
    valid_until: str | None = None
    superseded_by: str | None = None


class SecurityInfo(BaseModel):
    classification: str = "public_demo"
    redaction_applied: bool = False


class ClaimAuditInfo(BaseModel):
    created_at: str
    updated_at: str


class RepoProvenanceInfo(BaseModel):
    repo_path: str
    git_root: str | None = None
    commit_sha: str | None = None
    dirty: bool = False
    dirty_paths: list[str] = Field(default_factory=list)
    scanner_version: str


class MemoryClaim(BaseModel):
    claim_id: str
    team_id: str
    repo_id: str | None = None
    scan_id: str
    entity: MemoryEntity
    relation: MemoryRelation
    evidence: MemoryEvidence
    extraction: ExtractionInfo
    governance: GovernanceInfo
    temporal: TemporalInfo = Field(default_factory=TemporalInfo)
    security: SecurityInfo = Field(default_factory=SecurityInfo)
    audit: ClaimAuditInfo


class MemoryValidationSummary(BaseModel):
    citation_validity: float
    unsupported_claim_rate: float
    secret_leakage_count: int
    structural_claims: int
    semantic_candidate_claims: int
    auto_promoted_semantic_claims: int
    warnings: list[str] = Field(default_factory=list)


class MemoryScanResult(BaseModel):
    schema_version: str = "memory-scan-v0"
    scan_id: str
    team_id: str
    repo_name: str | None = None
    created_at: str
    provenance: RepoProvenanceInfo | None = None
    sources: list[SourceRecord] = Field(default_factory=list)
    claims: list[MemoryClaim] = Field(default_factory=list)
    validation: MemoryValidationSummary
    summary: str
    warnings: list[str] = Field(default_factory=list)


class MemoryEvalResult(BaseModel):
    evaluation_id: str
    scan_id: str
    team_id: str
    repo_name: str | None = None
    created_at: str
    citation_validity: float
    unsupported_claim_rate: float
    secret_leakage_count: int
    structural_claims: int
    semantic_candidate_claims: int
    auto_promoted_semantic_claims: int
    pass_status: str
    recommendations: list[str] = Field(default_factory=list)
    markdown_report: str
