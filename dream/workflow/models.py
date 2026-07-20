# SPDX-License-Identifier: Apache-2.0

from typing import Literal

from pydantic import BaseModel, Field


class EngineeringLoopRequest(BaseModel):
    team_id: str = "demo_team"
    repo_path: str = "examples/java-demo-repo"
    repo_name: str | None = "java-demo-repo"
    raw_request: str
    pr_diff_path: str | None = "examples/fake_pr_diff.diff"
    pr_diff_text: str | None = None
    target_files: list[str] | None = None
    llm_provider: str = "openai-responses"
    testgen_dry_run: bool = False
    strict_eval: bool = False
    run_llm_judge: bool = True


class EngineeringLoopStage(BaseModel):
    stage: Literal["memory", "jira", "pr_review", "testgen", "eval"]
    status: str
    summary: str
    artifact_paths: list[str] = Field(default_factory=list)
    score: float | None = None
    model_provider: str | None = None
    model_name: str | None = None
    warnings: list[str] = Field(default_factory=list)


class EngineeringLoopResult(BaseModel):
    workflow_id: str
    status: str
    team_id: str
    repo_name: str
    case_id: str
    created_at: str
    stages: list[EngineeringLoopStage]
    overall_eval_score: float
    evidence_count: int
    generated_test_files: list[str] = Field(default_factory=list)
    summary_markdown: str
    json_path: str
    markdown_path: str
    warnings: list[str] = Field(default_factory=list)
