# SPDX-License-Identifier: Apache-2.0

from typing import ClassVar

from pydantic import BaseModel, Field


class TestGenRequest(BaseModel):
    __test__: ClassVar[bool] = False

    team_id: str
    repo_path: str
    target_language: str = "java"
    target_files: list[str] | None = None
    change_context: str | None = None
    coverage_report_path: str | None = None
    dry_run: bool = True
    max_targets: int = Field(default=3, ge=1, le=8)


class TestGenPlan(BaseModel):
    __test__: ClassVar[bool] = False

    run_id: str
    provider_name: str
    target_summary: str
    planned_actions: list[str]
    warnings: list[str] = Field(default_factory=list)


class TestGenResult(BaseModel):
    __test__: ClassVar[bool] = False

    run_id: str
    provider_name: str
    status: str
    generated_files: list[str]
    report_markdown: str
    warnings: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    model_provider: str | None = None
    model_name: str | None = None


class TestGenReport(BaseModel):
    __test__: ClassVar[bool] = False

    run_id: str
    coverage_before: float | None = None
    coverage_after: float | None = None
    execution_time_seconds: float | None = None
    generated_files: list[str]
    validation_status: str
    human_review_required: bool = True
