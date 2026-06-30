# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.context.repository import ContextArtifactRepository
from dream.context.service import ContextIntelligenceService
from dream.evals.evidence import EvalProfileLoader
from dream.evals.models import EvaluationDimension, EvaluationResult, EvaluationScorecard
from dream.evals.repository import EvaluationRepository
from dream.evals.scorecard import grade_for_score, make_dimension, pass_status_for_score
from dream.evals.templates import render_scorecard_report


class ContextEvaluationService:
    def __init__(
        self,
        *,
        context_service: ContextIntelligenceService | None = None,
        profile_loader: EvalProfileLoader | None = None,
        repository: EvaluationRepository | None = None,
        audit_logger: AuditLogger | None = None,
        artifact_repository: ContextArtifactRepository | None = None,
    ) -> None:
        self.context_service = context_service or ContextIntelligenceService()
        self.profile_loader = profile_loader or EvalProfileLoader()
        self.repository = repository or EvaluationRepository()
        self.audit_logger = audit_logger or AuditLogger()
        self.artifact_repository = artifact_repository or ContextArtifactRepository()

    def evaluate_case(self, *, case_id: str, profile_id: str) -> EvaluationResult:
        pack = self.context_service.assemble_case(case_id)
        profile = self.profile_loader.load(pack.team_id, profile_id)
        text = _pack_text(pack)
        dimensions = [
            _coverage_dimension("expected_concept_coverage", text, profile.expected_concepts),
            _coverage_dimension("expected_doc_coverage", text, profile.expected_docs),
            _coverage_dimension("expected_code_coverage", text, profile.expected_code),
            _coverage_dimension("expected_test_coverage", text, profile.expected_tests),
            _coverage_dimension("expected_incident_coverage", text, profile.expected_incidents),
            _coverage_dimension("historical_jira_coverage", text, profile.expected_jira),
            _coverage_dimension("historical_pr_coverage", text, profile.expected_pr),
            make_dimension(
                name="source_type_coverage",
                score=_source_type_score(pack),
                weight=1.0,
                rationale="Checks diversity across docs, code, tests, incidents, Jira, and PR.",
                evidence=_source_types(pack),
                missing_items=[],
                recommendations=["Add missing source categories to the knowledge pack or graph."],
            ),
            make_dimension(
                name="graph_path_coverage",
                score=10.0 if pack.graph_paths else 4.0,
                weight=1.0,
                rationale="Checks whether Evidence Graph Lite contributed paths.",
                evidence=[path.path for path in pack.graph_paths],
                missing_items=[] if pack.graph_paths else ["No graph paths selected."],
                recommendations=["Run dream graph build for the target repo."]
                if not pack.graph_paths
                else [],
            ),
            make_dimension(
                name="approved_memory_ratio",
                score=_approved_memory_score(pack),
                weight=1.0,
                rationale="Checks whether selected memory claims are approved.",
                evidence=[claim.claim_id for claim in pack.selected_memory_claims],
                missing_items=[],
                recommendations=["Review candidate memory claims before generation."]
                if pack.candidate_memory_claims
                else [],
            ),
        ]
        missing = [
            item
            for dimension in dimensions
            for item in dimension.missing_items
            if item
        ]
        overall = sum(dimension.score * dimension.weight for dimension in dimensions) / sum(
            dimension.weight for dimension in dimensions
        )
        scorecard = EvaluationScorecard(
            evaluation_id=f"eval-retrieval-{uuid4().hex[:12]}",
            target_type="retrieval_context",
            target_id=pack.context_pack_id,
            case_id=case_id,
            team_id=pack.team_id,
            repo_name=pack.repo_name,
            created_at=datetime.now(UTC).isoformat(),
            overall_score=overall,
            grade=grade_for_score(overall),
            pass_status=pass_status_for_score(overall, missing),
            dimensions=dimensions,
            missing_critical_items=missing,
            source_coverage={source_type: True for source_type in _source_types(pack)},
            recommendations=_recommendations(dimensions),
            evaluated_artifact_path=pack.markdown_path,
        )
        markdown = render_scorecard_report(scorecard)
        from dream.core.paths import display_path, resolve_artifact_path

        eval_dir = resolve_artifact_path("evals")
        eval_dir.mkdir(parents=True, exist_ok=True)
        json_path = eval_dir / f"{scorecard.evaluation_id}.json"
        markdown_path = eval_dir / f"{scorecard.evaluation_id}.md"
        scorecard.output_path = display_path(markdown_path)
        json_path.write_text(scorecard.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        self.repository.save(scorecard)
        self.audit_logger.log_generation(
            run_id=scorecard.evaluation_id,
            use_case="retrieval_context_eval",
            team_id=pack.team_id,
            case_id=case_id,
            repo_name=pack.repo_name,
            input_payload={"case_id": case_id, "profile": profile_id},
            retrieved_source_paths=_pack_sources(pack),
            model_provider="deterministic",
            model_name="retrieval-context-eval-v1",
            output_path=display_path(markdown_path),
            status=scorecard.pass_status,
            warnings=[],
        )
        return EvaluationResult(
            scorecard=scorecard,
            markdown_report=markdown,
            json_path=display_path(json_path),
            markdown_path=display_path(markdown_path),
            warnings=[],
        )


def _coverage_dimension(name: str, text: str, expected: list[str]) -> EvaluationDimension:
    present = [item for item in expected if _present(text, item)]
    missing = [item for item in expected if item not in present]
    score = 10.0 if not expected else min(10.0, 10.0 * len(present) / len(expected))
    return make_dimension(
        name=name,
        score=score,
        weight=1.0,
        rationale=f"Checks {name.replace('_', ' ')} against eval profile.",
        evidence=present,
        missing_items=missing,
        recommendations=["Add missing expected evidence to retrieval context."] if missing else [],
    )


def _present(text: str, item: str) -> bool:
    lower = text.lower()
    value = item.lower()
    basename = value.replace("\\", "/").split("/")[-1]
    normalized_text = lower.replace("_", " ").replace("-", " ")
    normalized_value = value.replace("_", " ").replace("-", " ")
    return value in lower or basename in lower or normalized_value in normalized_text


def _pack_text(pack) -> str:
    return "\n".join(
        [
            pack.user_request,
            *[item.source_path for item in _all_evidence(pack)],
            *[item.title for item in _all_evidence(pack)],
            *[item.excerpt for item in _all_evidence(pack)],
            *[path.path for path in pack.graph_paths],
        ]
    )


def _all_evidence(pack):
    return (
        pack.selected_docs
        + pack.selected_code
        + pack.selected_tests
        + pack.selected_incidents
        + pack.selected_historical_jira
        + pack.selected_historical_pr
    )


def _source_types(pack) -> list[str]:
    return sorted({item.source_type for item in _all_evidence(pack)})


def _source_type_score(pack) -> float:
    useful = {
        "code_file",
        "test_file",
        "incident",
        "historical_jira",
        "historical_pr",
        "architecture",
        "domain",
        "knowledge_doc",
    }
    present = {item.source_type for item in _all_evidence(pack)}
    return min(10.0, 2.0 + len(present.intersection(useful)) * 1.25)


def _approved_memory_score(pack) -> float:
    total = len(pack.selected_memory_claims) + len(pack.candidate_memory_claims)
    if total == 0:
        return 6.0
    return 10.0 * len(pack.selected_memory_claims) / total


def _pack_sources(pack) -> list[str]:
    return sorted({item.source_path for item in _all_evidence(pack)})


def _recommendations(dimensions: list[EvaluationDimension]) -> list[str]:
    values: list[str] = []
    for dimension in dimensions:
        values.extend(dimension.recommendations)
    return list(dict.fromkeys(values))
