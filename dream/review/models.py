# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


class PRReviewRequest(BaseModel):
    team_id: str
    pr_diff_path: str | None = None
    pr_diff_text: str | None = None
    jira_context_path: str | None = None
    jira_context_text: str | None = None
    repo_name: str | None = None
    app: str | None = None
    component: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    llm_provider: str = "mock"
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class PRReviewResponse(BaseModel):
    run_id: str
    markdown: str
    sources_used: list[str]
    warnings: list[str] = Field(default_factory=list)
    memory_claims_used: list[str] = Field(default_factory=list)
    blocked_memory_claim_ids: list[str] = Field(default_factory=list)
    context_trail_id: str | None = None
