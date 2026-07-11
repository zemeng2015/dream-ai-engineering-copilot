# SPDX-License-Identifier: Apache-2.0

from typing import Literal

from pydantic import BaseModel, Field

from dream.llm.base import LLMReceipt

MemoryKind = Literal["preference", "policy", "episode"]
MemoryStatus = Literal["active", "superseded", "expired", "forgotten"]
MemoryAction = Literal["remember", "supersede", "forget", "ignore"]


class ExperienceObservation(BaseModel):
    team_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    source_reference: str | None = None
    occurred_at: str | None = None


class MemoryActionProposal(BaseModel):
    action: MemoryAction
    kind: MemoryKind | None = None
    key: str | None = None
    value: str | None = None
    target_memory_id: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: int = Field(default=3, ge=1, le=5)
    ttl_days: int | None = Field(default=None, ge=1, le=3650)
    rationale: str = Field(min_length=1)


class ExperiencePolicyResult(BaseModel):
    proposal: MemoryActionProposal
    provider_name: str
    model_name: str
    token_usage: dict[str, int] | None = None
    llm_receipt: LLMReceipt | None = None


class ExperienceMemory(BaseModel):
    schema_version: str = "experience-memory-v1"
    memory_id: str
    team_id: str
    user_id: str
    kind: MemoryKind
    key: str
    value: str
    status: MemoryStatus = "active"
    confidence: float = Field(ge=0.0, le=1.0)
    importance: int = Field(ge=1, le=5)
    source_session_id: str
    source_reference: str
    created_at: str
    updated_at: str
    valid_from: str
    valid_until: str | None = None
    superseded_by: str | None = None
    last_recalled_at: str | None = None
    recall_count: int = Field(default=0, ge=0)
    feedback_count: int = Field(default=0, ge=0)
    helpful_total: int = 0
    correctness_total: int = 0


class ExperienceDecisionRecord(BaseModel):
    schema_version: str = "experience-decision-v1"
    decision_id: str
    team_id: str
    user_id: str
    session_id: str
    requested_action: MemoryAction
    action: MemoryAction
    target_memory_id: str | None = None
    created_memory_id: str | None = None
    rationale: str
    provider_name: str
    model_name: str
    token_usage: dict[str, int] | None = None
    llm_receipt: LLMReceipt | None = None
    created_at: str


class ExperienceCaptureResult(BaseModel):
    decision: ExperienceDecisionRecord
    memory: ExperienceMemory | None = None
    affected_memories: list[ExperienceMemory] = Field(default_factory=list)
    active_memory_count: int


class ExperienceRecallRequest(BaseModel):
    team_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    token_budget: int = Field(default=512, ge=32, le=8192)
    limit: int = Field(default=12, ge=1, le=50)


class ExperienceRecallCandidate(BaseModel):
    memory: ExperienceMemory
    score: float
    estimated_tokens: int
    selected: bool
    reason: str


class ExperienceRecallResult(BaseModel):
    team_id: str
    user_id: str
    session_id: str
    query: str
    token_budget: int
    estimated_tokens_used: int
    selected: list[ExperienceRecallCandidate] = Field(default_factory=list)
    excluded: list[ExperienceRecallCandidate] = Field(default_factory=list)
    expired_memory_ids: list[str] = Field(default_factory=list)
    context_card: str


class ExperienceFeedbackRequest(BaseModel):
    team_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    helpful: bool
    correct: bool

