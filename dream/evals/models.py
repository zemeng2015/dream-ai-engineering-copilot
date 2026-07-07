# SPDX-License-Identifier: Apache-2.0

from typing import Literal

from pydantic import BaseModel, Field


class HumanRating(BaseModel):
    run_id: str
    usefulness_score: int = Field(ge=1, le=5)
    correctness_score: int = Field(ge=1, le=5)
    comments: str
    created_at: str


class EvaluationDimension(BaseModel):
    name: str
    score: float = Field(ge=0, le=10)
    weight: float = Field(gt=0)
    passed: bool
    rationale: str
    evidence: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class LLMJudgeResult(BaseModel):
    status: Literal["completed", "failed"]
    provider: str | None = None
    model: str | None = None
    prompt_version: str = "llm-judge-v1"
    input_hash: str | None = None
    duration_ms: int | None = None
    readiness: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    summary: str | None = None
    risks: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    raw_response: str | None = None
    token_usage: dict[str, int] | None = None
    warning: str | None = None


class EvaluationScorecard(BaseModel):
    evaluation_id: str
    target_type: str
    target_id: str | None = None
    run_id: str | None = None
    case_id: str | None = None
    team_id: str | None = None
    repo_name: str | None = None
    created_at: str
    overall_score: float
    grade: str
    pass_status: str
    dimensions: list[EvaluationDimension]
    missing_critical_items: list[str] = Field(default_factory=list)
    hallucination_warnings: list[str] = Field(default_factory=list)
    source_coverage: dict[str, bool] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    llm_judge: LLMJudgeResult | None = None
    evaluated_artifact_path: str | None = None
    output_path: str | None = None
    json_path: str | None = None
    markdown_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    target_type: str
    target_id: str | None = None
    case_id: str | None = None
    run_id: str | None = None
    artifact_path: str | None = None
    team_id: str | None = None
    repo_name: str | None = None
    strict: bool = False
    expected_profile: str | None = None
    judge_provider: str = "none"


class EvaluationJudgeRequest(BaseModel):
    judge_provider: str = "openai-compatible"


class EvaluationResult(BaseModel):
    scorecard: EvaluationScorecard
    markdown_report: str
    json_path: str
    markdown_path: str
    warnings: list[str] = Field(default_factory=list)


class EvalProfile(BaseModel):
    profile_id: str
    title: str
    query_patterns: list[str] = Field(default_factory=list)
    expected_concepts: list[str] = Field(default_factory=list)
    expected_code: list[str] = Field(default_factory=list)
    expected_tests: list[str] = Field(default_factory=list)
    expected_docs: list[str] = Field(default_factory=list)
    expected_incidents: list[str] = Field(default_factory=list)
    expected_jira: list[str] = Field(default_factory=list)
    expected_pr: list[str] = Field(default_factory=list)
    expected_roles: list[str] = Field(default_factory=list)
    critical_questions: dict[str, list[str]] = Field(default_factory=dict)
    critical_risks: list[str] = Field(default_factory=list)
    minimum_score_to_pass: float = 7.0
