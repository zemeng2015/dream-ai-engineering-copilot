# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.core.paths import display_path, ensure_artifacts_dir, resolve_project_path
from dream.testgen.models import TestGenPlan, TestGenRequest, TestGenResult


class MockTestGenProvider:
    provider_name = "mock"

    def __init__(self, *, audit_logger: AuditLogger | None = None) -> None:
        self.audit_logger = audit_logger or AuditLogger()

    def plan(self, request: TestGenRequest) -> TestGenPlan:
        run_id = f"testgen-plan-{uuid4().hex[:12]}"
        repo_path = resolve_project_path(request.repo_path, must_exist=True)
        targets = self._target_files(repo_path, request)
        planned_actions = [
            "Inspect target source files without modifying the repository.",
            "Suggest deterministic test file names for human review.",
            "Write a mock report under artifacts/ only.",
        ]
        return TestGenPlan(
            run_id=run_id,
            provider_name=self.provider_name,
            target_summary=self._target_summary(targets),
            planned_actions=planned_actions,
            warnings=["Mock provider does not generate production tests."],
        )

    def run(self, request: TestGenRequest) -> TestGenResult:
        run_id = f"testgen-{uuid4().hex[:12]}"
        repo_path = resolve_project_path(request.repo_path, must_exist=True)
        targets = self._target_files(repo_path, request)
        suggested_files = [self._suggest_test_path(path) for path in targets]
        warnings = [
            "Mock provider did not modify the repository.",
            "Generated test suggestions require human review.",
        ]
        markdown = self._render_report(
            run_id=run_id,
            request=request,
            target_files=targets,
            generated_files=suggested_files,
            warnings=warnings,
        )
        output_path = ensure_artifacts_dir() / f"testgen-report-{run_id}.md"
        output_path.write_text(markdown, encoding="utf-8")
        self.audit_logger.log_generation(
            run_id=run_id,
            use_case="testgen_run",
            team_id=request.team_id,
            input_payload=request.model_dump(),
            retrieved_source_paths=[],
            model_provider=self.provider_name,
            model_name="mock-testgen-v1",
            output_path=display_path(output_path),
            status="dry_run" if request.dry_run else "mock_success",
            warnings=warnings,
        )
        return TestGenResult(
            run_id=run_id,
            provider_name=self.provider_name,
            status="dry_run" if request.dry_run else "mock_success",
            generated_files=suggested_files,
            report_markdown=markdown,
            warnings=warnings,
        )

    @staticmethod
    def _target_files(repo_path: Path, request: TestGenRequest) -> list[str]:
        if request.target_files:
            return sorted(request.target_files)
        source_root = repo_path / "src" / "main"
        if not source_root.exists():
            return []
        extension = ".java" if request.target_language.lower() == "java" else ""
        return sorted(
            path.relative_to(repo_path).as_posix()
            for path in source_root.rglob(f"*{extension}")
            if path.is_file()
        )

    @staticmethod
    def _suggest_test_path(source_path: str) -> str:
        path = Path(source_path)
        if "src/main/java" in source_path:
            candidate = source_path.replace("src/main/java", "src/test/java")
        else:
            candidate = f"tests/{path.stem}Test{path.suffix}"
        candidate_path = Path(candidate)
        return candidate_path.with_name(
            f"{candidate_path.stem}GeneratedTest{candidate_path.suffix}"
        ).as_posix()

    @staticmethod
    def _target_summary(target_files: list[str]) -> str:
        if not target_files:
            return "No target source files discovered."
        return f"{len(target_files)} target file(s): {', '.join(target_files)}"

    def _render_report(
        self,
        *,
        run_id: str,
        request: TestGenRequest,
        target_files: list[str],
        generated_files: list[str],
        warnings: list[str],
    ) -> str:
        targets = "\n".join(f"- {path}" for path in target_files) or "- None"
        generated = "\n".join(f"- {path}" for path in generated_files) or "- None"
        warning_lines = "\n".join(f"- {warning}" for warning in warnings)
        return f"""# Mock TestGen Report

Run ID: {run_id}
Provider: {self.provider_name}
Team: {request.team_id}
Dry run: {request.dry_run}
Human review required: true

## Target Summary
{self._target_summary(target_files)}

## Target Files
{targets}

## Suggested Generated Files
{generated}

## Validation Status
mock-not-executed

## Warnings
{warning_lines}
"""
