# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class RequirementDraftRequest(BaseModel):
    team_id: str
    rough_business_request: str
    app: str | None = None
    component: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    llm_provider: str = "mock"


class RequirementDraftResponse(BaseModel):
    run_id: str
    markdown: str
    sources_used: list[str]
    warnings: list[str] = Field(default_factory=list)
