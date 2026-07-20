# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.core.paths import display_path, resolve_artifact_path
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationRequest
from dream.graph import EvidenceGraphBuilder
from dream.llm import BaseLLMProvider
from dream.memory import MemoryDistillationEvaluator, MemoryDistillationService
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.review import PRReviewAssistant, PRReviewRequest
from dream.testgen import JTestGenAdapter, TestGenRequest
from dream.workflow.models import (
    EngineeringLoopRequest,
    EngineeringLoopResult,
    EngineeringLoopStage,
)


class EngineeringLoopService:
    """Run DREAM's governed engineering change loop as one auditable workflow."""

    def __init__(
        self,
        *,
        llm_provider: BaseLLMProvider,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.audit_logger = audit_logger or AuditLogger()

    def run(self, request: EngineeringLoopRequest) -> EngineeringLoopResult:
        workflow_id = f"engineering-loop-{uuid4().hex[:12]}"
        created_at = datetime.now(UTC).isoformat()
        stages: list[EngineeringLoopStage] = []

        scan = MemoryDistillationService().scan(
            team_id=request.team_id,
            repo_path=request.repo_path,
            repo_name=request.repo_name,
        )
        memory_eval = MemoryDistillationEvaluator().evaluate(
            team_id=request.team_id, scan_id=scan.scan_id
        )
        memory_repository = MemoryDistillationRepository()
        graph = EvidenceGraphBuilder().build(
            team_id=request.team_id,
            repo_name=scan.repo_name,
        )
        stages.append(
            EngineeringLoopStage(
                stage="memory",
                status="governed",
                summary=(
                    f"Distilled {len(scan.claims)} claims from {len(scan.sources)} sources; "
                    f"built {len(graph.nodes)} evidence nodes."
                ),
                artifact_paths=[
                    memory_repository.display_scan_path(request.team_id, scan.scan_id),
                    memory_repository.display_eval_path(
                        request.team_id, memory_eval.evaluation_id
                    ),
                ],
                score=round(memory_eval.citation_validity * 10, 2),
                warnings=scan.warnings,
            )
        )

        requirement_service = RequirementCaseService(llm_provider=self.llm_provider)
        snapshot = requirement_service.create_case(
            RequirementCaseCreateRequest(
                team_id=request.team_id,
                raw_request=request.raw_request,
                created_by_role="ENGINEER",
            )
        )
        snapshot = requirement_service.analyze_case(snapshot.case.case_id)
        requirement_service.generate_engineering_brief(snapshot.case.case_id)
        jira = requirement_service.generate_jira_draft(snapshot.case.case_id)
        readiness = requirement_service.jira_readiness(snapshot.case.case_id)
        jira_path = f"artifacts/requirement-cases/{snapshot.case.case_id}/jira-draft.md"
        stages.append(
            EngineeringLoopStage(
                stage="jira",
                status=readiness.status,
                summary=(
                    f"Created a source-backed Jira draft with {len(snapshot.evidence)} evidence "
                    f"items and {readiness.open_questions} governed open question(s)."
                ),
                artifact_paths=[jira_path],
                model_provider=getattr(
                    requirement_service.jira_generator, "last_model_provider", None
                ),
                model_name=getattr(requirement_service.jira_generator, "last_model_name", None),
                warnings=jira.warnings,
            )
        )

        review = PRReviewAssistant(llm_provider=self.llm_provider).review(
            PRReviewRequest(
                team_id=request.team_id,
                pr_diff_path=request.pr_diff_path,
                pr_diff_text=request.pr_diff_text,
                jira_context_text=jira.markdown,
                repo_name=scan.repo_name,
                top_k=8,
                llm_provider=request.llm_provider,
            )
        )
        review_path = f"artifacts/pr-review-summary-{review.run_id}.md"
        stages.append(
            EngineeringLoopStage(
                stage="pr_review",
                status="completed_needs_human_review",
                summary=(
                    f"Reviewed the change against {len(review.sources_used)} memory/code sources."
                ),
                artifact_paths=[review_path],
                model_provider=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                warnings=review.warnings,
            )
        )

        testgen = JTestGenAdapter(llm_provider=self.llm_provider).run(
            TestGenRequest(
                team_id=request.team_id,
                repo_path=request.repo_path,
                target_language="java",
                target_files=request.target_files,
                change_context=(
                    f"ORIGINAL CHANGE REQUEST:\n{request.raw_request}\n\n"
                    f"GOVERNED JIRA DRAFT:\n{jira.markdown}"
                ),
                dry_run=request.testgen_dry_run,
                max_targets=3,
            )
        )
        stages.append(
            EngineeringLoopStage(
                stage="testgen",
                status=testgen.status,
                summary=(
                    f"JTestGen produced {len(testgen.generated_files)} isolated test candidate(s)."
                ),
                artifact_paths=[path for path in [testgen.artifact_path] if path],
                model_provider=testgen.model_provider,
                model_name=testgen.model_name,
                warnings=testgen.warnings,
            )
        )

        judge_provider = self.llm_provider if request.run_llm_judge else None
        evaluator = EvaluationAgent(llm_judge_provider=judge_provider)
        eval_requests = [
            EvaluationRequest(
                target_type="jira_draft",
                case_id=snapshot.case.case_id,
                team_id=request.team_id,
                repo_name=scan.repo_name,
                strict=request.strict_eval,
            ),
            EvaluationRequest(
                target_type="pr_review",
                run_id=review.run_id,
                team_id=request.team_id,
                repo_name=scan.repo_name,
                strict=request.strict_eval,
            ),
            EvaluationRequest(
                target_type="testgen_report",
                artifact_path=testgen.artifact_path,
                team_id=request.team_id,
                repo_name=scan.repo_name,
                strict=request.strict_eval,
            ),
        ]
        eval_results = [evaluator.evaluate(item) for item in eval_requests]
        scores = [item.scorecard.overall_score for item in eval_results]
        overall_score = round(sum(scores) / len(scores), 2)
        stages.append(
            EngineeringLoopStage(
                stage="eval",
                status=(
                    "pass"
                    if all(item.scorecard.pass_status == "pass" for item in eval_results)
                    else "needs_review"
                ),
                summary=(
                    "Scored Jira, PR review, and test generation artifacts with deterministic "
                    f"rubrics{' plus GPT-5.6 judge' if judge_provider else ''}."
                ),
                artifact_paths=[item.markdown_path for item in eval_results],
                score=overall_score,
                model_provider=self.llm_provider.provider_name if judge_provider else None,
                model_name=self.llm_provider.model_name if judge_provider else None,
                warnings=[warning for item in eval_results for warning in item.warnings],
            )
        )

        status = "completed" if readiness.ready and all(
            item.scorecard.pass_status == "pass" for item in eval_results
        ) else "completed_needs_review"
        warnings = list(dict.fromkeys(warning for stage in stages for warning in stage.warnings))
        summary = self._render_summary(
            workflow_id=workflow_id,
            status=status,
            request=request,
            case_id=snapshot.case.case_id,
            stages=stages,
            overall_score=overall_score,
        )
        output_dir = resolve_artifact_path(Path("engineering-loop") / workflow_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / "summary.md"
        json_path = output_dir / "summary.json"
        markdown_path.write_text(summary, encoding="utf-8")
        result = EngineeringLoopResult(
            workflow_id=workflow_id,
            status=status,
            team_id=request.team_id,
            repo_name=scan.repo_name,
            case_id=snapshot.case.case_id,
            created_at=created_at,
            stages=stages,
            overall_eval_score=overall_score,
            evidence_count=len(snapshot.evidence),
            generated_test_files=testgen.generated_files,
            summary_markdown=summary,
            json_path=display_path(json_path),
            markdown_path=display_path(markdown_path),
            warnings=warnings,
        )
        json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        self.audit_logger.log_generation(
            run_id=workflow_id,
            use_case="engineering_change_loop",
            team_id=request.team_id,
            case_id=snapshot.case.case_id,
            repo_name=scan.repo_name,
            input_payload=request.model_dump(),
            retrieved_source_paths=sorted({item.source_path for item in snapshot.evidence}),
            model_provider=self.llm_provider.provider_name,
            model_name=self.llm_provider.model_name,
            output_path=display_path(markdown_path),
            status=status,
            warnings=warnings,
        )
        return result

    @staticmethod
    def _render_summary(
        *,
        workflow_id: str,
        status: str,
        request: EngineeringLoopRequest,
        case_id: str,
        stages: list[EngineeringLoopStage],
        overall_score: float,
    ) -> str:
        stage_lines = []
        for stage in stages:
            score = f" | score {stage.score:.2f}" if stage.score is not None else ""
            stage_lines.append(
                f"- **{stage.stage}** — {stage.status}{score}: {stage.summary}"
            )
        return f"""# DREAM Engineering Change Loop

Workflow ID: {workflow_id}
Status: {status}
Case ID: {case_id}
Model provider: {request.llm_provider}
Overall eval score: {overall_score:.2f}/10

## Change Request
{request.raw_request}

## Governed Loop
{chr(10).join(stage_lines)}

## Safety Boundary
- Jira remains a draft; DREAM does not publish it to Jira.
- PR review is advisory and requires a human reviewer.
- JTestGen writes only isolated artifacts and never mutates the target repository.
- Eval results expose missing evidence and unresolved questions instead of hiding them.

## Codex + GPT-5.6
- Codex was used to design, implement, test, and document this end-to-end workflow.
- GPT-5.6 runs through the native Responses API for Jira drafting, PR review,
  JTestGen generation, and optional LLM-as-judge evaluation.
"""
