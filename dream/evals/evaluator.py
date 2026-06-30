# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.core.errors import DreamError, NotFoundError
from dream.core.paths import display_path, resolve_artifact_path, resolve_project_path
from dream.evals.evidence import EvalProfileLoader, EvidenceCoverageAnalyzer
from dream.evals.models import (
    EvalProfile,
    EvaluationDimension,
    EvaluationRequest,
    EvaluationResult,
    EvaluationScorecard,
)
from dream.evals.repository import EvaluationRepository
from dream.evals.scorecard import (
    PR_REVIEW_DIMENSION_WEIGHTS,
    REQUIREMENT_DIMENSION_WEIGHTS,
    TESTGEN_DIMENSION_WEIGHTS,
    grade_for_score,
    make_dimension,
    pass_status_for_score,
    score_fraction,
    weighted_average,
)
from dream.evals.templates import render_scorecard_report
from dream.requirement_cases.repository import RequirementCaseRepository


@dataclass
class EvaluationTarget:
    markdown: str
    sources: list[str]
    target_id: str | None = None
    case_id: str | None = None
    run_id: str | None = None
    team_id: str | None = None
    repo_name: str | None = None
    artifact_path: str | None = None
    warnings: list[str] | None = None


class EvaluationAgent:
    def __init__(
        self,
        *,
        repository: EvaluationRepository | None = None,
        audit_repository: AuditRepository | None = None,
        audit_logger: AuditLogger | None = None,
        requirement_repository: RequirementCaseRepository | None = None,
        profile_loader: EvalProfileLoader | None = None,
        coverage_analyzer: EvidenceCoverageAnalyzer | None = None,
    ) -> None:
        self.repository = repository or EvaluationRepository()
        self.audit_repository = audit_repository or AuditRepository()
        self.audit_logger = audit_logger or AuditLogger(repository=self.audit_repository)
        self.requirement_repository = requirement_repository or RequirementCaseRepository()
        self.profile_loader = profile_loader or EvalProfileLoader()
        self.coverage_analyzer = coverage_analyzer or EvidenceCoverageAnalyzer()

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        target = self._load_target(request)
        team_id = request.team_id or target.team_id
        repo_name = request.repo_name or target.repo_name
        profile = self._profile_for_request(request, target.markdown, team_id)
        source_coverage = self.coverage_analyzer.analyze(target.markdown, target.sources)
        dimensions = self._evaluate_dimensions(
            target_type=request.target_type,
            markdown=target.markdown,
            sources=target.sources,
            source_coverage=source_coverage,
            profile=profile,
        )
        missing_critical_items = self._missing_critical_items(
            markdown=target.markdown,
            sources=target.sources,
            profile=profile,
            strict=request.strict,
        )
        hallucination_warnings = self._hallucination_warnings(
            target.markdown,
            source_coverage,
        )
        overall_score = weighted_average(dimensions)
        if (
            profile
            and profile.minimum_score_to_pass > 7.0
            and overall_score < profile.minimum_score_to_pass
        ):
            missing_critical_items.append(
                f"Overall score is below profile threshold {profile.minimum_score_to_pass:.1f}."
            )
        scorecard = EvaluationScorecard(
            evaluation_id=f"eval-{uuid4().hex[:12]}",
            target_type=request.target_type,
            target_id=request.target_id or target.target_id,
            run_id=request.run_id or target.run_id,
            case_id=request.case_id or target.case_id,
            team_id=team_id,
            repo_name=repo_name,
            created_at=datetime.now(UTC).isoformat(),
            overall_score=overall_score,
            grade=grade_for_score(overall_score),
            pass_status=pass_status_for_score(overall_score, missing_critical_items),
            dimensions=dimensions,
            missing_critical_items=_dedupe(missing_critical_items),
            hallucination_warnings=hallucination_warnings,
            source_coverage=source_coverage,
            recommendations=self._recommendations(dimensions, missing_critical_items),
            evaluated_artifact_path=target.artifact_path,
        )
        result = self._persist_result(scorecard, target, request)
        self.audit_logger.log_generation(
            run_id=scorecard.evaluation_id,
            use_case="evaluation_scorecard",
            team_id=team_id or "unknown",
            case_id=scorecard.case_id,
            repo_name=repo_name,
            input_payload=request.model_dump(),
            retrieved_source_paths=target.sources,
            model_provider="deterministic",
            model_name="evaluation-agent-v1",
            output_path=result.markdown_path,
            status=scorecard.pass_status,
            warnings=result.warnings,
        )
        return result

    def _load_target(self, request: EvaluationRequest) -> EvaluationTarget:
        if request.artifact_path:
            markdown, artifact_path = self._read_artifact(request.artifact_path)
            return EvaluationTarget(
                markdown=markdown,
                sources=[artifact_path],
                target_id=request.target_id or artifact_path,
                team_id=request.team_id,
                repo_name=request.repo_name,
                artifact_path=artifact_path,
                warnings=[],
            )
        if request.run_id:
            record = self.audit_repository.get_audit_record(request.run_id)
            if record is None:
                raise NotFoundError(f"Audit run not found: {request.run_id}")
            if record.output_path.startswith("sqlite:") and record.case_id:
                case_target = self._load_case_target(record.case_id, request.target_type)
                case_target.run_id = record.run_id
                return case_target
            markdown, artifact_path = self._read_artifact(record.output_path)
            return EvaluationTarget(
                markdown=markdown,
                sources=record.retrieved_source_paths,
                target_id=request.target_id or record.run_id,
                case_id=record.case_id,
                run_id=record.run_id,
                team_id=record.team_id,
                repo_name=record.repo_name,
                artifact_path=artifact_path,
                warnings=record.warnings,
            )
        if request.case_id:
            return self._load_case_target(request.case_id, request.target_type)
        raise DreamError("Evaluation requires artifact_path, run_id, or case_id.")

    def _load_case_target(self, case_id: str, target_type: str) -> EvaluationTarget:
        snapshot = self.requirement_repository.get(case_id)
        sources = sorted({item.source_path for item in snapshot.evidence})
        if target_type == "engineering_brief" and snapshot.engineering_brief:
            return EvaluationTarget(
                markdown=snapshot.engineering_brief.markdown,
                sources=snapshot.engineering_brief.sources_used or sources,
                target_id=case_id,
                case_id=case_id,
                team_id=snapshot.case.team_id,
                artifact_path=None,
                warnings=snapshot.engineering_brief.warnings,
            )
        if target_type == "jira_draft" and snapshot.jira_draft:
            return EvaluationTarget(
                markdown=snapshot.jira_draft.markdown,
                sources=snapshot.jira_draft.sources_used or sources,
                target_id=case_id,
                case_id=case_id,
                team_id=snapshot.case.team_id,
                artifact_path=None,
                warnings=snapshot.jira_draft.warnings,
            )
        if target_type == "impact_map":
            markdown = self._render_impact_map(snapshot)
        elif target_type == "role_questions":
            markdown = self._render_questions(snapshot)
        else:
            markdown = self._render_requirement_case(snapshot)
        return EvaluationTarget(
            markdown=markdown,
            sources=sources,
            target_id=case_id,
            case_id=case_id,
            team_id=snapshot.case.team_id,
            warnings=snapshot.warnings,
        )

    def _evaluate_dimensions(
        self,
        *,
        target_type: str,
        markdown: str,
        sources: list[str],
        source_coverage: dict[str, bool],
        profile: EvalProfile | None,
    ) -> list[EvaluationDimension]:
        if target_type == "pr_review":
            return self._evaluate_pr_review(markdown, sources, source_coverage, profile)
        if target_type == "testgen_report":
            return self._evaluate_testgen_report(markdown, source_coverage)
        if target_type == "role_questions":
            return self._evaluate_role_questions(markdown, sources, source_coverage, profile)
        if target_type == "impact_map":
            return self._evaluate_impact_map(markdown, sources, source_coverage, profile)
        return self._evaluate_requirement_like(
            target_type, markdown, sources, source_coverage, profile
        )

    def _evaluate_requirement_like(
        self,
        target_type: str,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        profile: EvalProfile | None,
    ) -> list[EvaluationDimension]:
        weights = REQUIREMENT_DIMENSION_WEIGHTS
        headings = _headings_for_requirement_target(target_type)
        heading_score, missing_headings = self._section_score(markdown, headings)
        dimensions = [
            make_dimension(
                name="completeness",
                score=heading_score,
                weight=weights["completeness"],
                rationale="Checks whether the expected professional output sections are present.",
                evidence=[
                    f"{len(headings) - len(missing_headings)} of {len(headings)} sections found."
                ],
                missing_items=missing_headings,
                recommendations=["Add the missing sections before handoff."]
                if missing_headings
                else [],
            ),
            self._evidence_dimension(markdown, sources, coverage, weights["evidence_quality"]),
            self._profile_dimension(
                name="impact_accuracy",
                weight=weights["impact_accuracy"],
                markdown=markdown,
                sources=sources,
                profile=profile,
                groups=("expected_concepts", "expected_code"),
                fallback_terms=["workflow", "backend", "api", "data", "test", "ops", "frontend"],
                recommendation="Tie impact claims to concrete files, docs, or domain concepts.",
            ),
            self._role_coverage_dimension(markdown, profile, weights["role_coverage"]),
            self._test_awareness_dimension(markdown, sources, profile, weights["test_awareness"]),
            self._historical_context_dimension(
                markdown, sources, coverage, profile, weights["historical_context"]
            ),
            self._actionability_dimension(markdown, weights["actionability"]),
            self._specificity_dimension(markdown, sources, profile, weights["specificity"]),
            self._hallucination_dimension(markdown, coverage, weights["hallucination_risk"]),
        ]
        return dimensions

    def _evaluate_impact_map(
        self,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        profile: EvalProfile | None,
    ) -> list[EvaluationDimension]:
        weights = REQUIREMENT_DIMENSION_WEIGHTS
        area_terms = ["frontend", "backend", "api", "data", "workflow", "test", "ops", "security"]
        present_areas = self._present_items(markdown, area_terms)
        return [
            make_dimension(
                name="completeness",
                score=score_fraction(len(present_areas), 6),
                weight=weights["completeness"],
                rationale="Checks whether the impact map spans multiple engineering areas.",
                evidence=present_areas,
                missing_items=[term for term in area_terms[:6] if term not in present_areas],
                recommendations=["Map the request across workflow, backend/API, tests, and ops."],
            ),
            self._evidence_dimension(markdown, sources, coverage, weights["evidence_quality"]),
            self._profile_dimension(
                name="impact_accuracy",
                weight=weights["impact_accuracy"],
                markdown=markdown,
                sources=sources,
                profile=profile,
                groups=("expected_concepts", "expected_code", "expected_tests"),
                fallback_terms=area_terms,
                recommendation="Reference concrete impacted classes, UI areas, tests, and docs.",
            ),
            self._test_awareness_dimension(markdown, sources, profile, weights["test_awareness"]),
            self._actionability_dimension(markdown, weights["actionability"]),
            self._specificity_dimension(markdown, sources, profile, weights["specificity"]),
            self._hallucination_dimension(markdown, coverage, weights["hallucination_risk"]),
        ]

    def _evaluate_role_questions(
        self,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        profile: EvalProfile | None,
    ) -> list[EvaluationDimension]:
        weights = REQUIREMENT_DIMENSION_WEIGHTS
        question_count = markdown.count("?") + markdown.lower().count("why:")
        return [
            make_dimension(
                name="completeness",
                score=score_fraction(question_count, 8),
                weight=weights["completeness"],
                rationale="Checks whether there are enough clarification prompts for review.",
                evidence=[f"{question_count} question-like prompts found."],
                missing_items=[] if question_count >= 6 else ["Too few clarification questions."],
                recommendations=[
                    "Add questions that expose business, technical, QA, and ops uncertainty."
                ],
            ),
            self._evidence_dimension(markdown, sources, coverage, weights["evidence_quality"]),
            self._role_coverage_dimension(markdown, profile, weights["role_coverage"]),
            self._profile_dimension(
                name="impact_accuracy",
                weight=weights["impact_accuracy"],
                markdown=markdown,
                sources=sources,
                profile=profile,
                groups=("expected_concepts", "critical_risks"),
                fallback_terms=["status", "api", "test", "runbook", "polling", "retry"],
                recommendation=(
                    "Anchor questions to the likely impacted workflow and failure modes."
                ),
            ),
            self._test_awareness_dimension(markdown, sources, profile, weights["test_awareness"]),
            self._actionability_dimension(markdown, weights["actionability"]),
            self._specificity_dimension(markdown, sources, profile, weights["specificity"]),
            self._hallucination_dimension(markdown, coverage, weights["hallucination_risk"]),
        ]

    def _evaluate_pr_review(
        self,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        profile: EvalProfile | None,
    ) -> list[EvaluationDimension]:
        weights = PR_REVIEW_DIMENSION_WEIGHTS
        changed_file_terms = [".java", "changed files", "OutputCollector.java"]
        memory_terms = ["related codebase memory", "codebase", ".java", "test"]
        return [
            self._term_dimension(
                "changed_file_awareness",
                weights["changed_file_awareness"],
                markdown,
                changed_file_terms,
                "Checks whether the review names or summarizes changed files.",
                "List changed files and explain why each matters.",
            ),
            self._term_dimension(
                "codebase_memory_usage",
                weights["codebase_memory_usage"],
                "\n".join([markdown, *sources]),
                memory_terms,
                "Checks whether codebase memory is used beyond raw diff text.",
                "Use codebase index results for related symbols, tests, and concepts.",
            ),
            self._term_dimension(
                "business_alignment",
                weights["business_alignment"],
                markdown,
                ["dfp-", "business", "idempotency"],
                "Checks whether the review links code changes to requirement intent.",
                "Connect findings to Jira context and acceptance criteria.",
            ),
            self._term_dimension(
                "test_gap_detection",
                weights["test_gap_detection"],
                markdown,
                ["test", "regression", "missing", "coverage"],
                "Checks whether the review identifies test coverage and gaps.",
                "Add explicit missing test scenarios and affected test files.",
            ),
            self._term_dimension(
                "operational_risk_awareness",
                weights["operational_risk_awareness"],
                markdown,
                ["runbook", "ops", "incident", "retry", "duplicate", "idempotency"],
                "Checks whether runtime and operational risks are surfaced.",
                "Call out failure modes, monitoring, retry, and runbook impact.",
            ),
            self._historical_context_dimension(
                markdown, sources, coverage, profile, weights["historical_context"]
            ),
            self._actionability_dimension(markdown, weights["actionability"]),
            self._hallucination_dimension(markdown, coverage, weights["hallucination_risk"]),
        ]

    def _evaluate_testgen_report(
        self,
        markdown: str,
        coverage: dict[str, bool],
    ) -> list[EvaluationDimension]:
        weights = TESTGEN_DIMENSION_WEIGHTS
        return [
            self._term_dimension(
                "target_selection_quality",
                weights["target_selection_quality"],
                markdown,
                ["target", "source", "test", ".java", ".py", ".ts"],
                "Checks whether the report explains selected test targets.",
                "Name target files and why they need tests.",
            ),
            self._term_dimension(
                "validation_clarity",
                weights["validation_clarity"],
                markdown,
                ["validation", "dry-run", "status", "report"],
                "Checks whether validation status is clear.",
                "Explain what was validated and what remains unvalidated.",
            ),
            self._term_dimension(
                "coverage_reporting",
                weights["coverage_reporting"],
                markdown,
                ["coverage", "before", "after"],
                "Checks whether coverage reporting is present or explicitly unavailable.",
                "Include coverage before/after or state why it is unavailable.",
            ),
            self._term_dimension(
                "human_review_readiness",
                weights["human_review_readiness"],
                markdown,
                ["human review", "review required", "manual review"],
                "Checks whether generated tests are clearly routed to human review.",
                "State that generated tests require human review.",
            ),
            self._term_dimension(
                "safety",
                weights["safety"],
                markdown,
                ["dry-run", "no files were modified", "does not modify", "mock"],
                "Checks whether the report communicates safe mock/plugin behavior.",
                "Make dry-run behavior and repository safety explicit.",
            ),
            self._actionability_dimension(markdown, weights["actionability"]),
            self._hallucination_dimension(markdown, coverage, 1.0),
        ]

    def _evidence_dimension(
        self,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        weight: float,
    ) -> EvaluationDimension:
        covered = [name for name, present in coverage.items() if present]
        score = min(10.0, len(covered) * 1.1 + (2.0 if sources else 0.0))
        missing = []
        if not sources and "sources used" not in markdown.lower():
            missing.append("No source list or source metadata detected.")
        if len(covered) < 3:
            missing.append("Low diversity of evidence categories.")
        return make_dimension(
            name="evidence_quality",
            score=score,
            weight=weight,
            rationale=(
                "Checks source-backed grounding across docs, code, tests, incidents, "
                "Jira, and PR memory."
            ),
            evidence=covered,
            missing_items=missing,
            recommendations=["Cite retrieved docs, code files, tests, incidents, Jira, and PRs."],
        )

    def _profile_dimension(
        self,
        *,
        name: str,
        weight: float,
        markdown: str,
        sources: list[str],
        profile: EvalProfile | None,
        groups: tuple[str, ...],
        fallback_terms: list[str],
        recommendation: str,
    ) -> EvaluationDimension:
        text = self._combined_text(markdown, sources)
        expected = []
        if profile:
            for group in groups:
                expected.extend(getattr(profile, group, []))
        else:
            expected = fallback_terms
        present = self._present_items(text, expected)
        missing = [item for item in expected if item not in present]
        return make_dimension(
            name=name,
            score=score_fraction(len(present), len(expected), empty_score=5.0),
            weight=weight,
            rationale="Checks expected concepts and concrete implementation references.",
            evidence=present,
            missing_items=missing,
            recommendations=[recommendation] if missing else [],
        )

    def _role_coverage_dimension(
        self,
        markdown: str,
        profile: EvalProfile | None,
        weight: float,
    ) -> EvaluationDimension:
        roles = profile.expected_roles if profile else ["BA", "TL", "FE", "BE", "QA", "OPS"]
        present = [role for role in roles if self._role_present(markdown, role)]
        missing = [role for role in roles if role not in present]
        return make_dimension(
            name="role_coverage",
            score=score_fraction(len(present), len(roles), empty_score=6.0),
            weight=weight,
            rationale="Checks whether stakeholder-specific uncertainty is represented.",
            evidence=present,
            missing_items=missing,
            recommendations=["Add role-specific questions or review notes for missing roles."]
            if missing
            else [],
        )

    def _test_awareness_dimension(
        self,
        markdown: str,
        sources: list[str],
        profile: EvalProfile | None,
        weight: float,
    ) -> EvaluationDimension:
        text = self._combined_text(markdown, sources)
        expected = (
            profile.expected_tests if profile else ["test", "regression", "acceptance criteria"]
        )
        present = self._present_items(text, expected)
        if not profile:
            present = self._present_items(text, expected)
        missing = [item for item in expected if item not in present]
        return make_dimension(
            name="test_awareness",
            score=score_fraction(len(present), len(expected), empty_score=4.0),
            weight=weight,
            rationale=(
                "Checks whether test strategy, regression risk, and likely test files "
                "are considered."
            ),
            evidence=present,
            missing_items=missing,
            recommendations=["Name affected tests and missing regression scenarios."]
            if missing
            else [],
        )

    def _historical_context_dimension(
        self,
        markdown: str,
        sources: list[str],
        coverage: dict[str, bool],
        profile: EvalProfile | None,
        weight: float,
    ) -> EvaluationDimension:
        if profile:
            expected = profile.expected_incidents + profile.expected_jira + profile.expected_pr
            present = self._present_items(self._combined_text(markdown, sources), expected)
            missing = [item for item in expected if item not in present]
            score = score_fraction(len(present), len(expected), empty_score=5.0)
        else:
            categories = ["incidents", "historical_jira", "historical_pr"]
            present = [name for name in categories if coverage.get(name)]
            missing = [name for name in categories if not coverage.get(name)]
            score = score_fraction(len(present), len(categories), empty_score=4.0)
        return make_dimension(
            name="historical_context",
            score=score,
            weight=weight,
            rationale="Checks whether incident, Jira, and PR history inform the output.",
            evidence=present,
            missing_items=missing,
            recommendations=["Reference relevant incidents, prior stories, and PR review lessons."]
            if missing
            else [],
        )

    def _actionability_dimension(self, markdown: str, weight: float) -> EvaluationDimension:
        lower = markdown.lower()
        bullets = sum(1 for line in markdown.splitlines() if line.strip().startswith("- "))
        action_terms = self._present_items(
            lower,
            [
                "acceptance criteria",
                "open questions",
                "dev notes",
                "test strategy",
                "review checklist",
            ],
        )
        score = min(10.0, bullets * 0.6 + len(action_terms) * 1.5)
        missing = (
            [] if score >= 7.0 else ["Output needs more concrete next steps or review prompts."]
        )
        return make_dimension(
            name="actionability",
            score=score,
            weight=weight,
            rationale="Checks whether a human reviewer can act on the output.",
            evidence=[f"{bullets} bullets found.", *action_terms],
            missing_items=missing,
            recommendations=[
                "Add acceptance criteria, test scenarios, open questions, and reviewer prompts."
            ]
            if missing
            else [],
        )

    def _specificity_dimension(
        self,
        markdown: str,
        sources: list[str],
        profile: EvalProfile | None,
        weight: float,
    ) -> EvaluationDimension:
        text = self._combined_text(markdown, sources)
        if profile:
            expected = (
                profile.expected_concepts
                + profile.expected_code
                + profile.expected_docs
                + profile.expected_incidents
                + profile.expected_jira
                + profile.expected_pr
            )
        else:
            expected = ["QUEUED", "RUNNING", "FAILED", "COMPLETED", ".java", ".ts", ".py"]
        present = self._present_items(text, expected)
        missing = [item for item in expected if item not in present]
        return make_dimension(
            name="specificity",
            score=score_fraction(len(present), len(expected), empty_score=5.0),
            weight=weight,
            rationale="Checks whether the output uses precise domain, code, and memory references.",
            evidence=present,
            missing_items=missing[:12],
            recommendations=[
                "Replace generic statements with named components, statuses, docs, and tests."
            ]
            if missing
            else [],
        )

    def _hallucination_dimension(
        self,
        markdown: str,
        coverage: dict[str, bool],
        weight: float,
    ) -> EvaluationDimension:
        warnings = self._hallucination_warnings(markdown, coverage)
        score = 9.0 - len(warnings) * 1.5
        return make_dimension(
            name="hallucination_risk",
            score=score,
            weight=weight,
            rationale=(
                "Checks for unsupported certainty, missing grounding, and unsafe review "
                "claims."
            ),
            evidence=[] if warnings else ["No high-risk unsupported claims detected."],
            missing_items=warnings,
            recommendations=["Qualify uncertainty and ground claims in cited evidence."]
            if warnings
            else [],
        )

    def _term_dimension(
        self,
        name: str,
        weight: float,
        markdown: str,
        terms: list[str],
        rationale: str,
        recommendation: str,
    ) -> EvaluationDimension:
        present = self._present_items(markdown, terms)
        missing = [term for term in terms if term not in present]
        return make_dimension(
            name=name,
            score=score_fraction(len(present), len(terms), empty_score=4.0),
            weight=weight,
            rationale=rationale,
            evidence=present,
            missing_items=missing,
            recommendations=[recommendation] if missing else [],
        )

    def _profile_for_request(
        self,
        request: EvaluationRequest,
        markdown: str,
        team_id: str | None,
    ) -> EvalProfile | None:
        if not team_id:
            return None
        if request.expected_profile:
            return self.profile_loader.load(team_id, request.expected_profile)
        return self.profile_loader.infer(team_id, markdown)

    def _missing_critical_items(
        self,
        *,
        markdown: str,
        sources: list[str],
        profile: EvalProfile | None,
        strict: bool,
    ) -> list[str]:
        if not profile:
            return []
        text = self._combined_text(markdown, sources)
        missing = [item for item in profile.critical_risks if not self._item_present(text, item)]
        if strict:
            expected = (
                profile.expected_concepts
                + profile.expected_code
                + profile.expected_tests
                + profile.expected_docs
                + profile.expected_incidents
                + profile.expected_jira
                + profile.expected_pr
            )
            missing.extend(item for item in expected if not self._item_present(text, item))
        return missing

    def _hallucination_warnings(
        self,
        markdown: str,
        coverage: dict[str, bool],
    ) -> list[str]:
        lower = markdown.lower()
        warnings = []
        if not any(coverage.values()) and "sources used" not in lower:
            warnings.append("No source-backed references detected.")
        risky_claims = ["approved", "safe to merge", "guaranteed", "no risk", "must be correct"]
        warnings.extend(
            f"Unsupported certainty phrase detected: {claim}"
            for claim in risky_claims
            if claim in lower
        )
        if "human review" not in lower and ("pr review" in lower or "generated" in lower):
            warnings.append("Human review requirement is not stated.")
        return _dedupe(warnings)

    @staticmethod
    def _section_score(markdown: str, required_sections: list[str]) -> tuple[float, list[str]]:
        lower = markdown.lower()
        missing = [section for section in required_sections if section.lower() not in lower]
        return score_fraction(
            len(required_sections) - len(missing), len(required_sections)
        ), missing

    @staticmethod
    def _combined_text(markdown: str, sources: list[str]) -> str:
        return "\n".join([markdown, *sources]).lower()

    def _present_items(self, text: str, items: list[str]) -> list[str]:
        return [item for item in items if self._item_present(text, item)]

    @staticmethod
    def _item_present(text: str, item: str) -> bool:
        lower = text.lower()
        value = item.lower()
        basename = value.replace("\\", "/").split("/")[-1]
        normalized_text = lower.replace("_", " ").replace("-", " ")
        normalized_value = value.replace("_", " ").replace("-", " ")
        tokens = [token for token in normalized_value.split() if len(token) > 2]
        return (
            value in lower
            or basename in lower
            or normalized_value in normalized_text
            or (len(tokens) > 1 and all(token in normalized_text for token in tokens))
        )

    @staticmethod
    def _role_present(markdown: str, role: str) -> bool:
        upper_role = role.upper()
        candidates = [
            f"## {upper_role}",
            f"### {upper_role}",
            f"[{upper_role}]",
            f"{upper_role}:",
            f"- {upper_role}",
            f"**{upper_role}**",
        ]
        return any(candidate in markdown for candidate in candidates)

    @staticmethod
    def _read_artifact(path_value: str) -> tuple[str, str]:
        path = resolve_project_path(path_value, must_exist=True)
        if path.is_dir():
            raise DreamError(f"Evaluation artifact is a directory: {path_value}")
        return path.read_text(encoding="utf-8"), display_path(path)

    @staticmethod
    def _render_requirement_case(snapshot) -> str:
        evidence_lines = (
            "\n".join(
                f"- {item.title} ({item.source_type}): {item.source_path}"
                for item in snapshot.evidence
            )
            or "- No retrieved context."
        )
        impact_lines = (
            "\n".join(
                f"- {item.area_type}: {item.name} - {item.reason}" for item in snapshot.impact_items
            )
            or "- No impact map generated."
        )
        question_lines = (
            "\n".join(
                f"- [{item.target_role}] {item.question} Why: {item.why_it_matters}"
                for item in snapshot.questions
            )
            or "- No clarification questions generated."
        )
        return f"""# Requirement Case

## Request
{snapshot.case.raw_request}

## Retrieved Context
{evidence_lines}

## Impact Map
{impact_lines}

## Role-specific Clarification Questions
{question_lines}
"""

    @staticmethod
    def _render_impact_map(snapshot) -> str:
        lines = ["# Impact Map", ""]
        for item in snapshot.impact_items:
            lines.append(f"- {item.area_type}: {item.name}")
            lines.append(f"  - Description: {item.description}")
            lines.append(f"  - Confidence: {item.confidence:.2f}")
            lines.append(f"  - Sources: {', '.join(item.sources) or 'inferred'}")
            lines.append(f"  - Reason: {item.reason}")
        if not snapshot.impact_items:
            lines.append("- No impact map generated.")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_questions(snapshot) -> str:
        lines = ["# Role-specific Clarification Questions", ""]
        for question in snapshot.questions:
            lines.append(f"## {question.target_role}")
            lines.append(f"- {question.question}")
            lines.append(f"- Why: {question.why_it_matters}")
            lines.append(f"- Sources: {', '.join(question.related_sources) or 'inferred'}")
            lines.append("")
        if not snapshot.questions:
            lines.append("- No clarification questions generated.")
        return "\n".join(lines)

    def _persist_result(
        self,
        scorecard: EvaluationScorecard,
        target: EvaluationTarget,
        request: EvaluationRequest,
    ) -> EvaluationResult:
        eval_dir = resolve_artifact_path("evals")
        eval_dir.mkdir(parents=True, exist_ok=True)
        json_path = eval_dir / f"{scorecard.evaluation_id}.json"
        markdown_path = eval_dir / f"{scorecard.evaluation_id}.md"
        scorecard.output_path = display_path(markdown_path)
        markdown_report = render_scorecard_report(scorecard)
        json_path.write_text(scorecard.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(markdown_report, encoding="utf-8")
        self.repository.save(scorecard)
        warnings = list(target.warnings or [])
        if request.expected_profile:
            warnings.append(f"Used eval profile: {request.expected_profile}")
        return EvaluationResult(
            scorecard=scorecard,
            markdown_report=markdown_report,
            json_path=display_path(json_path),
            markdown_path=display_path(markdown_path),
            warnings=_dedupe(warnings),
        )

    @staticmethod
    def _recommendations(
        dimensions: list[EvaluationDimension],
        missing_critical_items: list[str],
    ) -> list[str]:
        recommendations = []
        for dimension in dimensions:
            recommendations.extend(dimension.recommendations)
        if missing_critical_items:
            recommendations.append(
                "Resolve critical missing items before treating this output as ready."
            )
        return _dedupe(recommendations)


def _headings_for_requirement_target(target_type: str) -> list[str]:
    if target_type == "engineering_brief":
        return [
            "# Engineering Brief",
            "## 1. Request Summary",
            "## 4. Impact Map",
            "## 6. Role-specific Clarification Questions",
            "## 8. Test Strategy",
            "## 11. Sources Used",
        ]
    if target_type == "jira_draft":
        return [
            "# Jira Story Draft",
            "## User Story",
            "## Acceptance Criteria",
            "## Test Scenarios",
            "## Open Questions",
            "## Sources Used",
        ]
    if target_type == "requirement_case":
        return [
            "# Requirement Case",
            "## Request",
            "## Retrieved Context",
            "## Impact Map",
            "## Role-specific Clarification Questions",
        ]
    return ["#", "## Sources Used"]


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
