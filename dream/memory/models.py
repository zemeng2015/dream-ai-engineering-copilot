# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


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
    access: ResourceAccess = Field(default_factory=ResourceAccess)


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


class MemoryIntakeSectionProof(BaseModel):
    section_id: str
    heading: str
    source_reference: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    section_hash: str | None = None


class MemoryIntakeProof(BaseModel):
    document_id: str
    draft_id: str | None = None
    original_path: str | None = None
    stored_path: str | None = None
    promoted_path: str
    source_hash: str | None = None
    source_hash_verified: bool | None = None
    review_status: str | None = None
    match_explanation: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    intake_audit_run_ids: list[str] = Field(default_factory=list)
    section_proofs: list[MemoryIntakeSectionProof] = Field(default_factory=list)


class MemoryEvidence(BaseModel):
    source_ids: list[str] = Field(default_factory=list)
    spans: list[MemoryEvidenceSpan] = Field(default_factory=list)
    intake_proofs: list[MemoryIntakeProof] = Field(default_factory=list)


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
    acl_scope: str = "local_demo"
    allowed_principal_ids: list[str] = Field(default_factory=list)
    allowed_group_ids: list[str] = Field(default_factory=list)
    source_acl_version: str | None = None

    def resource_access(self) -> ResourceAccess:
        return ResourceAccess.model_validate(
            {
                "classification": self.classification,
                "acl_scope": self.acl_scope,
                "allowed_principal_ids": self.allowed_principal_ids,
                "allowed_group_ids": self.allowed_group_ids,
                "source_acl_version": self.source_acl_version,
            }
        )


class ClaimAuditInfo(BaseModel):
    created_at: str
    updated_at: str


class MemoryReviewFieldDiff(BaseModel):
    field_path: str
    before: str | None = None
    after: str | None = None


class MemoryReviewClaimSnapshot(BaseModel):
    claim_id: str
    entity_type: str
    entity_name: str
    relation_type: str
    relation_value: str | None = None
    extraction_method: str
    confidence: float
    risk_level: str
    security_classification: str
    evidence_paths: list[str] = Field(default_factory=list)
    intake_document_ids: list[str] = Field(default_factory=list)
    source_hashes: list[str] = Field(default_factory=list)


class MemoryReviewSignalExplanation(BaseModel):
    signal: str
    category: str
    severity: str
    explanation: str
    evidence: list[str] = Field(default_factory=list)


class MemoryReviewEvent(BaseModel):
    event_id: str
    team_id: str
    claim_id: str
    scan_id: str
    previous_status: str
    new_status: str
    reviewer: str | None = None
    reason: str | None = None
    reviewed_at: str
    reviewer_signature: str | None = None
    field_diffs: list[MemoryReviewFieldDiff] = Field(default_factory=list)
    claim_snapshot: MemoryReviewClaimSnapshot | None = None
    risk_signals: list[str] = Field(default_factory=list)
    conflict_signals: list[str] = Field(default_factory=list)
    signal_explanations: list[MemoryReviewSignalExplanation] = Field(default_factory=list)


class MemoryLedgerSnapshot(BaseModel):
    team_id: str
    updated_at: str
    events: list[MemoryReviewEvent] = Field(default_factory=list)


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


class MemoryConflictClaimSide(BaseModel):
    claim: MemoryClaim
    effective_status: str
    relation_value: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    intake_document_ids: list[str] = Field(default_factory=list)
    latest_review: MemoryReviewEvent | None = None


class MemoryConflictPair(BaseModel):
    conflict_id: str
    team_id: str
    scan_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    relation_type: str
    left: MemoryConflictClaimSide
    right: MemoryConflictClaimSide
    signal: MemoryReviewSignalExplanation


class MemoryConflictReport(BaseModel):
    team_id: str
    scan_id: str
    generated_at: str
    conflict_count: int
    pairs: list[MemoryConflictPair] = Field(default_factory=list)


class MemoryConflictResolutionEvent(BaseModel):
    event_id: str
    team_id: str
    scan_id: str
    conflict_id: str
    action: str
    winning_claim_id: str
    rejected_claim_id: str
    reviewer: str | None = None
    reason: str | None = None
    resolved_at: str
    reviewer_signature: str | None = None
    review_event_ids: list[str] = Field(default_factory=list)
    conflict_snapshot: MemoryConflictPair


class MemoryConflictResolutionLedger(BaseModel):
    team_id: str
    updated_at: str
    events: list[MemoryConflictResolutionEvent] = Field(default_factory=list)


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


class MemoryClaimSearchResult(BaseModel):
    claim: MemoryClaim
    effective_status: str
    score: float
    reason: str
    review_event: MemoryReviewEvent | None = None


class MemoryClaimRetrievalBatch(BaseModel):
    results: list[MemoryClaimSearchResult] = Field(default_factory=list)
    blocked_claim_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MemoryDiffResult(BaseModel):
    team_id: str
    scan_id: str
    base_scan_id: str | None = None
    added_claims: list[MemoryClaim] = Field(default_factory=list)
    removed_claims: list[MemoryClaim] = Field(default_factory=list)
    changed_claims: list[MemoryClaim] = Field(default_factory=list)
    unchanged_count: int = 0
    markdown: str
