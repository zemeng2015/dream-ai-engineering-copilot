# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    run_id: str
    timestamp: str
    use_case: str
    team_id: str
    case_id: str | None = None
    repo_name: str | None = None
    input_hash: str
    retrieved_source_paths: list[str]
    model_provider: str
    model_name: str
    output_path: str
    status: str
    warnings: list[str] = Field(default_factory=list)
