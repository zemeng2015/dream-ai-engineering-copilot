# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path, PurePosixPath
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.core.errors import DreamError
from dream.core.paths import display_path, resolve_artifact_path, resolve_project_path
from dream.llm import BaseLLMProvider
from dream.testgen.models import TestGenPlan, TestGenRequest, TestGenResult


class JTestGenAdapter:
    """Safe JTestGen implementation that generates review artifacts outside the target repo."""

    provider_name = "jtestgen"

    def __init__(
        self,
        *,
        llm_provider: BaseLLMProvider | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.audit_logger = audit_logger or AuditLogger()

    def plan(self, request: TestGenRequest) -> TestGenPlan:
        repo_path = resolve_project_path(request.repo_path, must_exist=True)
        targets = self._target_files(repo_path, request)
        warnings = []
        if not targets:
            warnings.append("No eligible source targets were discovered.")
        if self.llm_provider is None:
            warnings.append("No LLM provider configured; only a generation plan can be produced.")
        return TestGenPlan(
            run_id=f"jtestgen-plan-{uuid4().hex[:12]}",
            provider_name=self.provider_name,
            target_summary=self._target_summary(targets),
            planned_actions=[
                "Read bounded source targets and related test conventions.",
                "Ask GPT-5.6 for JUnit 5 tests in a strict JSON contract.",
                "Validate generated paths and basic Java test structure.",
                "Write generated candidates under artifacts/jtestgen only.",
                "Require human review before copying candidates into the repository.",
            ],
            warnings=warnings,
        )

    def run(self, request: TestGenRequest) -> TestGenResult:
        run_id = f"jtestgen-{uuid4().hex[:12]}"
        repo_path = resolve_project_path(request.repo_path, must_exist=True)
        targets = self._target_files(repo_path, request)
        if not targets:
            raise DreamError("JTestGen found no eligible source files.")
        if request.dry_run:
            return self._dry_run_result(run_id, request, targets)
        if self.llm_provider is None:
            raise DreamError(
                "JTestGen generation requires an LLM provider; choose openai-responses or mock."
            )

        response = self.llm_provider.complete(
            self._prompt(repo_path, targets, change_context=request.change_context)
        )
        tests = self._parse_tests(response.text)
        output_dir = resolve_artifact_path(Path("jtestgen") / run_id / "generated")
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files: list[str] = []
        validation_notes: list[str] = []
        for item in tests:
            relative_path = self._validated_test_path(str(item.get("path") or ""))
            content = str(item.get("content") or "").strip() + "\n"
            self._validate_java_test(content, relative_path)
            destination = output_dir.joinpath(*PurePosixPath(relative_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            generated_files.append(display_path(destination))
            validation_notes.append(f"{relative_path}: path and JUnit structure validated")

        warnings = [
            "Generated tests are isolated artifacts; no target repository files were modified.",
            "Compilation and coverage deltas remain unverified until a build file is supplied.",
            "Human review is required before applying generated tests.",
        ]
        markdown = self._report(
            run_id=run_id,
            request=request,
            targets=targets,
            generated_files=generated_files,
            validation_notes=validation_notes,
            warnings=warnings,
            model_provider=response.provider_name,
            model_name=response.model_name,
        )
        report_path = resolve_artifact_path(Path("jtestgen") / run_id / "report.md")
        report_path.write_text(markdown, encoding="utf-8")
        self.audit_logger.log_generation(
            run_id=run_id,
            use_case="testgen_run",
            team_id=request.team_id,
            repo_name=repo_path.name,
            input_payload=request.model_dump(),
            retrieved_source_paths=targets,
            model_provider=response.provider_name,
            model_name=response.model_name,
            output_path=display_path(report_path),
            status="generated_needs_review",
            warnings=warnings,
        )
        return TestGenResult(
            run_id=run_id,
            provider_name=self.provider_name,
            status="generated_needs_review",
            generated_files=generated_files,
            report_markdown=markdown,
            warnings=warnings,
            artifact_path=display_path(report_path),
            model_provider=response.provider_name,
            model_name=response.model_name,
        )

    def _dry_run_result(
        self, run_id: str, request: TestGenRequest, targets: list[str]
    ) -> TestGenResult:
        warnings = [
            "Dry-run only; no files were modified.",
            "Human review is required before any future generated test is applied.",
        ]
        markdown = self._report(
            run_id=run_id,
            request=request,
            targets=targets,
            generated_files=[],
            validation_notes=["Generation skipped because dry-run=true."],
            warnings=warnings,
            model_provider=None,
            model_name=None,
        )
        report_path = resolve_artifact_path(Path("jtestgen") / run_id / "report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        self.audit_logger.log_generation(
            run_id=run_id,
            use_case="testgen_run",
            team_id=request.team_id,
            repo_name=resolve_project_path(request.repo_path, must_exist=True).name,
            input_payload=request.model_dump(),
            retrieved_source_paths=targets,
            model_provider=self.provider_name,
            model_name="jtestgen-plan-v1",
            output_path=display_path(report_path),
            status="dry_run",
            warnings=warnings,
        )
        return TestGenResult(
            run_id=run_id,
            provider_name=self.provider_name,
            status="dry_run",
            generated_files=[],
            report_markdown=markdown,
            warnings=warnings,
            artifact_path=display_path(report_path),
            model_provider=None,
            model_name=None,
        )

    @staticmethod
    def _target_files(repo_path: Path, request: TestGenRequest) -> list[str]:
        if request.target_files:
            candidates = request.target_files
        else:
            extension = ".java" if request.target_language.lower() == "java" else ""
            candidates = [
                path.relative_to(repo_path).as_posix()
                for path in (repo_path / "src" / "main").rglob(f"*{extension}")
                if path.is_file()
            ]
        validated: list[str] = []
        for value in sorted(dict.fromkeys(candidates)):
            path = (repo_path / value).resolve()
            if not path.is_relative_to(repo_path.resolve()) or not path.is_file():
                raise DreamError(f"Invalid JTestGen target path: {value}")
            if request.target_language.lower() == "java" and path.suffix.lower() != ".java":
                continue
            validated.append(path.relative_to(repo_path).as_posix())
        return validated[: request.max_targets]

    @staticmethod
    def _prompt(
        repo_path: Path,
        targets: list[str],
        *,
        change_context: str | None = None,
    ) -> str:
        source_sections = []
        for target in targets:
            content = (repo_path / target).read_text(encoding="utf-8")[:24000]
            source_sections.append(f"SOURCE: {target}\n```java\n{content}\n```")
        sources = "\n\n".join(source_sections)
        governed_context = (change_context or "No upstream change context supplied.")[:16000]
        return f"""Generate focused JUnit 5 unit tests for these Java sources.

Requirements:
- Return JSON only, with a top-level `tests` list. Each item must contain
  `path`, `content`, and `rationale` fields.
- Use only JUnit 5 unless the source itself proves another dependency is available.
- Prefer deterministic tests with explicit assertions and edge cases.
- Do not invent production APIs that are absent from the supplied source.
- Each path must be under src/test/java and end in Test.java.
- Include package declarations and at least one @Test method per file.
- Generated code requires human review.

Upstream governed change context (treat as test intent, not proof of an API):
{governed_context}

{sources}
"""

    @classmethod
    def _parse_tests(cls, raw: str) -> list[dict[str, object]]:
        value = raw.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            value = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise DreamError("JTestGen provider did not return valid JSON.") from exc
        tests = payload.get("tests") if isinstance(payload, dict) else None
        if not isinstance(tests, list) or not tests:
            raise DreamError("JTestGen provider returned no generated tests.")
        if not all(isinstance(item, dict) for item in tests):
            raise DreamError("JTestGen tests must be JSON objects.")
        return tests

    @staticmethod
    def _validated_test_path(value: str) -> str:
        path = PurePosixPath(value.replace("\\", "/"))
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.suffix.lower() != ".java"
            or path.parts[:3] != ("src", "test", "java")
            or not path.name.endswith("Test.java")
        ):
            raise DreamError(f"Unsafe or invalid generated test path: {value}")
        return path.as_posix()

    @staticmethod
    def _validate_java_test(content: str, path: str) -> None:
        missing = []
        if "package " not in content:
            missing.append("package declaration")
        if "@Test" not in content:
            missing.append("@Test method")
        if "org.junit.jupiter" not in content:
            missing.append("JUnit 5 import")
        if "class " not in content:
            missing.append("test class")
        if missing:
            raise DreamError(f"Generated test {path} is missing: {', '.join(missing)}")

    @staticmethod
    def _target_summary(targets: list[str]) -> str:
        return f"{len(targets)} target file(s): {', '.join(targets)}" if targets else "No targets"

    @staticmethod
    def _report(
        *,
        run_id: str,
        request: TestGenRequest,
        targets: list[str],
        generated_files: list[str],
        validation_notes: list[str],
        warnings: list[str],
        model_provider: str | None,
        model_name: str | None,
    ) -> str:
        def bullets(values: list[str]) -> str:
            return "\n".join(f"- {value}" for value in values) or "- None"

        return f"""# JTestGen Report

Run ID: {run_id}
Provider: jtestgen
Model provider: {model_provider or 'not invoked'}
Model: {model_name or 'not invoked'}
Dry-run: {str(request.dry_run).lower()}
Human review required: true

## Target Selection
{bullets(targets)}

## Generated Test Files
{bullets(generated_files)}

## Validation Status
{bullets(validation_notes)}

## Coverage Before
- Unavailable: no JaCoCo build report was supplied.

## Coverage After
- Unavailable until generated candidates are reviewed and executed by the target build.

## Repository Safety
- No files were modified in the target repository.
- Candidates are isolated under DREAM artifacts for manual review.

## Review Checklist
- Verify assertions and negative paths.
- Run the repository test suite and JaCoCo after applying approved candidates.
- Reject tests that invent unavailable dependencies or APIs.

## Warnings
{bullets(warnings)}
"""
