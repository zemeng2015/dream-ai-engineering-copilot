# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from pydantic import BaseModel, Field

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexRepository, CodebaseRetriever
from dream.context import ContextIntelligenceService
from dream.core.errors import DreamError
from dream.core.paths import ensure_artifacts_dir, get_audit_db_path
from dream.evals import EvaluationRequest
from dream.evals.evaluator import EvaluationAgent
from dream.evals.repository import EvaluationRepository
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRepository, EvidenceGraphRetriever
from dream.memory import (
    EngineeringMemoryRetriever,
    MemoryClaim,
    MemoryClaimRetriever,
    MemoryDistillationService,
)
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases import (
    RequirementCaseCreateRequest,
    RequirementCaseRepository,
    RequirementCaseService,
)

LEADERSHIP_DEMO_TEAM_ID = "demo_team"
LEADERSHIP_DEMO_REPO_NAME = "dfp-demo-repo"
LEADERSHIP_DEMO_REPO_PATH = "examples/dfp-demo-repo"
LEADERSHIP_DEMO_CASE_ID = "case-leadership-async-status"
LEADERSHIP_DEMO_SCAN_ID = "leadership-dfp-memory-v1"
LEADERSHIP_DEMO_PROFILE_ID = "async-status-tracking"
LEADERSHIP_DEMO_REVIEWER = "DREAM Leadership Demo Reviewer"
LEADERSHIP_DEMO_REQUEST = (
    "Users need better visibility when a forecast case takes too long. "
    "The execution page should show which task is still running, display "
    "task-level status, and refresh automatically."
)


class LeadershipDemoSeedResult(BaseModel):
    scenario_version: str = "leadership-dfp-v1"
    team_id: str = LEADERSHIP_DEMO_TEAM_ID
    repo_name: str = LEADERSHIP_DEMO_REPO_NAME
    repo_path: str = LEADERSHIP_DEMO_REPO_PATH
    case_id: str = LEADERSHIP_DEMO_CASE_ID
    scan_id: str = LEADERSHIP_DEMO_SCAN_ID
    approved_claim_id: str
    context_trail_id: str
    evaluation_id: str
    evidence_count: int
    source_paths: list[str] = Field(default_factory=list)
    open_question_ids: list[str] = Field(default_factory=list)
    jira_ready: bool
    reset_applied: bool


class LeadershipDemoService:
    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        artifacts_root = artifacts_dir or ensure_artifacts_dir()
        database_path = db_path or get_audit_db_path()
        self.audit_repository = AuditRepository(database_path)
        self.audit_logger = AuditLogger(repository=self.audit_repository)
        self.requirement_repository = RequirementCaseRepository(database_path)
        self.evaluation_repository = EvaluationRepository(database_path)
        self.codebase_repository = CodebaseIndexRepository(artifacts_root)
        self.graph_repository = EvidenceGraphRepository(artifacts_root)
        self.memory_repository = MemoryDistillationRepository(artifacts_root)

    def seed(self, *, reset: bool = False) -> LeadershipDemoSeedResult:
        existing = self.requirement_repository.try_get(LEADERSHIP_DEMO_CASE_ID)
        if existing is not None and not reset:
            raise DreamError(
                "Leadership demo data already exists. Re-run with reset enabled to "
                "replace the deterministic scenario."
            )
        if reset:
            self._reset_case_state()

        memory_service = MemoryDistillationService(
            repository=self.memory_repository,
            codebase_repository=self.codebase_repository,
            audit_logger=self.audit_logger,
        )
        scan = memory_service.scan(
            team_id=LEADERSHIP_DEMO_TEAM_ID,
            repo_path=LEADERSHIP_DEMO_REPO_PATH,
            repo_name=LEADERSHIP_DEMO_REPO_NAME,
            scan_id=LEADERSHIP_DEMO_SCAN_ID,
        )
        governed_claim = self._leadership_claim(scan.claims)
        self._reset_claim_review(governed_claim.claim_id)
        memory_service.review_claim(
            team_id=LEADERSHIP_DEMO_TEAM_ID,
            claim_id=governed_claim.claim_id,
            new_status="approved",
            reviewer=LEADERSHIP_DEMO_REVIEWER,
            reason=(
                "Approved synthetic Forecast Platform status-tracking guidance for "
                "the controlled leadership demonstration."
            ),
            scan_id=LEADERSHIP_DEMO_SCAN_ID,
        )

        EvidenceGraphBuilder(
            codebase_repository=self.codebase_repository,
            repository=self.graph_repository,
            audit_logger=self.audit_logger,
        ).build(
            team_id=LEADERSHIP_DEMO_TEAM_ID,
            repo_name=LEADERSHIP_DEMO_REPO_NAME,
        )

        requirement_service = self.requirement_service()
        requirement_service.create_case(
            RequirementCaseCreateRequest(
                team_id=LEADERSHIP_DEMO_TEAM_ID,
                raw_request=LEADERSHIP_DEMO_REQUEST,
                created_by_role="BA",
                target_app="ForecastDemo",
                target_component="ExecutionMonitor",
            ),
            case_id=LEADERSHIP_DEMO_CASE_ID,
        )
        analyzed = requirement_service.analyze_case(LEADERSHIP_DEMO_CASE_ID)
        gate_question_id = self._human_gate_question_id(analyzed.questions)
        for question in analyzed.questions:
            if question.question_id == gate_question_id:
                continue
            requirement_service.answer_question(
                LEADERSHIP_DEMO_CASE_ID,
                question.question_id,
                self._demo_answer(question.target_role),
                answered_by=LEADERSHIP_DEMO_REVIEWER,
            )
        requirement_service.generate_engineering_brief(LEADERSHIP_DEMO_CASE_ID)
        requirement_service.generate_jira_draft(LEADERSHIP_DEMO_CASE_ID)
        final_snapshot = requirement_service.get_case(LEADERSHIP_DEMO_CASE_ID)

        context_service = ContextIntelligenceService(
            requirement_repository=self.requirement_repository,
            graph_repository=self.graph_repository,
            memory_repository=self.memory_repository,
            codebase_repository=self.codebase_repository,
        )
        trail = context_service.trace_case(LEADERSHIP_DEMO_CASE_ID)
        context_service.assemble_case(LEADERSHIP_DEMO_CASE_ID)

        evaluation = EvaluationAgent(
            repository=self.evaluation_repository,
            audit_repository=self.audit_repository,
            audit_logger=self.audit_logger,
            requirement_repository=self.requirement_repository,
        ).evaluate(
            EvaluationRequest(
                target_type="jira_draft",
                case_id=LEADERSHIP_DEMO_CASE_ID,
                team_id=LEADERSHIP_DEMO_TEAM_ID,
                repo_name=LEADERSHIP_DEMO_REPO_NAME,
                expected_profile=LEADERSHIP_DEMO_PROFILE_ID,
            )
        )

        source_paths = sorted(
            {path for item in final_snapshot.evidence for path in item.provenance_paths()}
        )
        open_questions = [
            item.question_id for item in final_snapshot.questions if item.status == "open"
        ]
        return LeadershipDemoSeedResult(
            approved_claim_id=governed_claim.claim_id,
            context_trail_id=trail.trail_id,
            evaluation_id=evaluation.scorecard.evaluation_id,
            evidence_count=len(final_snapshot.evidence),
            source_paths=source_paths,
            open_question_ids=open_questions,
            jira_ready=bool(final_snapshot.jira_readiness and final_snapshot.jira_readiness.ready),
            reset_applied=reset,
        )

    def requirement_service(self) -> RequirementCaseService:
        codebase_retriever = CodebaseRetriever(repository=self.codebase_repository)
        graph_retriever = EvidenceGraphRetriever(repository=self.graph_repository)
        return RequirementCaseService(
            repository=self.requirement_repository,
            memory_retriever=EngineeringMemoryRetriever(
                codebase_repository=self.codebase_repository,
                codebase_retriever=codebase_retriever,
                graph_repository=self.graph_repository,
                graph_retriever=graph_retriever,
            ),
            memory_claim_retriever=MemoryClaimRetriever(repository=self.memory_repository),
            audit_logger=self.audit_logger,
            codebase_repository=self.codebase_repository,
        )

    def _reset_case_state(self) -> None:
        self.evaluation_repository.delete_case(LEADERSHIP_DEMO_CASE_ID)
        self.audit_repository.delete_case_records(LEADERSHIP_DEMO_CASE_ID)
        self.requirement_repository.delete(LEADERSHIP_DEMO_CASE_ID)

    def _reset_claim_review(self, claim_id: str) -> None:
        ledger = self.memory_repository.load_ledger(LEADERSHIP_DEMO_TEAM_ID)
        retained = [event for event in ledger.events if event.claim_id != claim_id]
        if len(retained) == len(ledger.events):
            return
        ledger.events = retained
        ledger.updated_at = retained[-1].reviewed_at if retained else ""
        self.memory_repository.save_ledger(ledger)

    @staticmethod
    def _leadership_claim(claims: list[MemoryClaim]) -> MemoryClaim:
        matches = [
            claim
            for claim in claims
            if claim.entity.canonical_name == "execution status"
            and claim.relation.type == "documented_by"
            and any(
                span.path.endswith("docs/architecture/status-tracking-design.md")
                for span in claim.evidence.spans
            )
        ]
        if len(matches) != 1:
            raise DreamError(
                "Leadership demo requires exactly one execution-status architecture claim; "
                f"found {len(matches)}."
            )
        return matches[0]

    @staticmethod
    def _human_gate_question_id(questions) -> str:
        matches = [
            item.question_id
            for item in questions
            if item.target_role == "BE" and "status transitions" in item.question.lower()
        ]
        if len(matches) != 1:
            raise DreamError(
                "Leadership demo requires one BE status-transition question to remain open."
            )
        return matches[0]

    @staticmethod
    def _demo_answer(role: str) -> str:
        answers = {
            "BA": "Use plain-language task status and preserve a visible partial state.",
            "TL": "Keep the first pilot inside the existing execution-status boundary.",
            "FE": "Poll every five seconds and show explicit loading, empty, and error states.",
            "BE": "Persist status for recovery; do not rely on process-local memory.",
            "QA": "Cover service, batch, timeout, partial, missing-job, and recovery paths.",
            "OPS": "Alert on stale RUNNING state and use the approved incident runbook.",
            "SECURITY": "Expose status metadata only; exclude request payload and result data.",
        }
        return answers.get(role, "Confirmed for the bounded synthetic leadership pilot.")
