# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


class RequirementCaseCreateRequest(BaseModel):
    team_id: str
    raw_request: str
    created_by_role: str | None = None
    target_app: str | None = None
    target_component: str | None = None
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class RequirementCase(BaseModel):
    case_id: str
    team_id: str
    title: str
    raw_request: str
    created_by_role: str | None = None
    target_app: str | None = None
    target_component: str | None = None
    status: str
    created_at: str
    updated_at: str
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class ContextEvidence(BaseModel):
    evidence_id: str
    case_id: str
    source_type: str
    source_path: str
    title: str
    excerpt: str
    relevance_score: float
    reason: str
    memory_claim_id: str | None = None
    governance_status: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    access: ResourceAccess = Field(default_factory=ResourceAccess)

    def provenance_paths(self) -> list[str]:
        return list(dict.fromkeys([self.source_path, *self.evidence_paths]))


class ImpactItem(BaseModel):
    impact_id: str
    case_id: str
    area_type: str
    name: str
    description: str
    confidence: float
    sources: list[str] = Field(default_factory=list)
    reason: str


class ClarificationQuestion(BaseModel):
    question_id: str
    case_id: str
    target_role: str
    question: str
    why_it_matters: str
    related_sources: list[str] = Field(default_factory=list)
    status: str = "open"
    answer: str | None = None
    answered_by: str | None = None
    answered_at: str | None = None
    waived_reason: str | None = None
    waived_by: str | None = None
    waived_at: str | None = None


class JiraReadiness(BaseModel):
    case_id: str
    ready: bool
    status: str
    answered_questions: int
    waived_questions: int = 0
    open_questions: int
    evidence_items: int
    impact_items: int
    jira_draft_exists: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class RoleView(BaseModel):
    case_id: str
    role: str
    markdown: str
    sources_used: list[str] = Field(default_factory=list)


class EngineeringBrief(BaseModel):
    case_id: str
    markdown: str
    sources_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JiraDraftContext(BaseModel):
    case_id: str
    deterministic_markdown: str
    prompt: str
    prompt_char_count: int
    deterministic_char_count: int
    sources_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JiraDraft(BaseModel):
    case_id: str
    markdown: str
    sources_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RequirementCaseSnapshot(BaseModel):
    case: RequirementCase
    evidence: list[ContextEvidence] = Field(default_factory=list)
    impact_items: list[ImpactItem] = Field(default_factory=list)
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    role_views: list[RoleView] = Field(default_factory=list)
    engineering_brief: EngineeringBrief | None = None
    jira_draft: JiraDraft | None = None
    jira_readiness: JiraReadiness | None = None
    warnings: list[str] = Field(default_factory=list)
