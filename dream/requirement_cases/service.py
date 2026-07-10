# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.codebase.repository import CodebaseIndexRepository
from dream.core.errors import NotFoundError
from dream.core.paths import display_path, resolve_artifact_path
from dream.llm import BaseLLMProvider
from dream.requirement_cases.brief import EngineeringBriefGenerator
from dream.requirement_cases.impact import ImpactMapGenerator
from dream.requirement_cases.jira import JiraDraftGenerator
from dream.requirement_cases.models import (
    ClarificationQuestion,
    ContextEvidence,
    EngineeringBrief,
    ImpactItem,
    JiraDraft,
    JiraDraftContext,
    JiraReadiness,
    RequirementCase,
    RequirementCaseCreateRequest,
    RequirementCaseSnapshot,
    RoleView,
)
from dream.requirement_cases.questions import QuestionGenerator
from dream.requirement_cases.repository import RequirementCaseRepository

if TYPE_CHECKING:
    from dream.memory import EngineeringMemoryRetriever, MemoryClaimRetriever


class RequirementCaseService:
    def __init__(
        self,
        *,
        repository: RequirementCaseRepository | None = None,
        memory_retriever: "EngineeringMemoryRetriever | None" = None,
        memory_claim_retriever: "MemoryClaimRetriever | None" = None,
        impact_generator: ImpactMapGenerator | None = None,
        question_generator: QuestionGenerator | None = None,
        brief_generator: EngineeringBriefGenerator | None = None,
        jira_generator: JiraDraftGenerator | None = None,
        audit_logger: AuditLogger | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        self.repository = repository or RequirementCaseRepository()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        if memory_retriever is None:
            from dream.memory import EngineeringMemoryRetriever as DefaultMemoryRetriever

            self.memory_retriever = DefaultMemoryRetriever()
        else:
            self.memory_retriever = memory_retriever
        if memory_claim_retriever is None:
            from dream.memory import MemoryClaimRetriever as DefaultMemoryClaimRetriever
            from dream.memory.repository import MemoryDistillationRepository

            self.memory_claim_retriever = DefaultMemoryClaimRetriever(
                repository=MemoryDistillationRepository(self.codebase_repository.artifacts_dir)
            )
        else:
            self.memory_claim_retriever = memory_claim_retriever
        self.impact_generator = impact_generator or ImpactMapGenerator()
        self.question_generator = question_generator or QuestionGenerator()
        self.brief_generator = brief_generator or EngineeringBriefGenerator(
            llm_provider=llm_provider
        )
        self.jira_generator = jira_generator or JiraDraftGenerator(llm_provider=llm_provider)
        self.audit_logger = audit_logger or AuditLogger()

    def create_case(
        self,
        request: RequirementCaseCreateRequest,
        *,
        case_id: str | None = None,
        created_at: str | None = None,
    ) -> RequirementCaseSnapshot:
        now = created_at or datetime.now(UTC).isoformat()
        case_id = case_id or f"case-{uuid4().hex[:12]}"
        case = RequirementCase(
            case_id=case_id,
            team_id=request.team_id,
            title=self._title(request.raw_request),
            raw_request=request.raw_request,
            created_by_role=request.created_by_role,
            target_app=request.target_app,
            target_component=request.target_component,
            status="created",
            created_at=now,
            updated_at=now,
        )
        snapshot = RequirementCaseSnapshot(case=case)
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=case_id,
            use_case="requirement_case_create",
            team_id=case.team_id,
            case_id=case.case_id,
            input_payload=request.model_dump(),
            retrieved_source_paths=[],
            model_provider="deterministic",
            model_name="requirement-case-v1",
            output_path="sqlite:requirement_cases",
            status="created",
            warnings=[],
        )
        return snapshot

    def analyze_case(self, case_id: str) -> RequirementCaseSnapshot:
        snapshot = self.repository.get(case_id)
        repo_name = self._default_repo_name(snapshot.case.team_id)
        evidence = self._with_case_id(
            snapshot.case.case_id,
            self.memory_retriever.search(
                team_id=snapshot.case.team_id,
                query=snapshot.case.raw_request,
                repo_name=repo_name,
                top_k=20,
                app=snapshot.case.target_app,
                component=snapshot.case.target_component,
            ),
        )
        governed_evidence, memory_warnings = self._approved_memory_claim_evidence(snapshot.case)
        evidence.extend(governed_evidence)
        impact_items = self.impact_generator.generate(snapshot.case, evidence)
        questions = self.question_generator.generate(snapshot.case, evidence)
        warnings = list(memory_warnings)
        if not evidence:
            warnings.append("No knowledge, codebase, or approved memory evidence was retrieved.")
        if repo_name is None:
            warnings.append(
                "No codebase index found for this team; analysis used knowledge docs only."
            )

        snapshot.evidence = evidence
        snapshot.impact_items = impact_items
        snapshot.questions = questions
        snapshot.warnings = warnings
        snapshot.case.status = "analyzed"
        snapshot.case.updated_at = datetime.now(UTC).isoformat()
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"req-analysis-{uuid4().hex[:12]}",
            use_case="requirement_case_analysis",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            repo_name=repo_name,
            input_payload={"case_id": case_id, "raw_request": snapshot.case.raw_request},
            retrieved_source_paths=_evidence_source_paths(evidence),
            model_provider="deterministic",
            model_name="requirement-case-analysis-v1",
            output_path="sqlite:requirement_cases",
            status="success",
            warnings=warnings,
        )
        from dream.context import ContextIntelligenceService

        ContextIntelligenceService(
            requirement_repository=self.repository,
            codebase_repository=self.codebase_repository,
            memory_repository=self.memory_claim_retriever.repository,
        ).trace_case(snapshot.case.case_id)
        return snapshot

    def _approved_memory_claim_evidence(
        self,
        case: RequirementCase,
    ) -> tuple[list[ContextEvidence], list[str]]:
        try:
            batch = self.memory_claim_retriever.search_with_policy(
                team_id=case.team_id,
                query=case.raw_request,
                top_k=8,
            )
        except NotFoundError:
            return [], ["No memory scan is available; governed MemoryClaims were not used."]

        evidence: list[ContextEvidence] = []
        for result in batch.results:
            claim = result.claim
            relation_value = claim.relation.value or claim.relation.object_entity_id or "_"
            condition = (
                f" Condition: {claim.relation.condition}." if claim.relation.condition else ""
            )
            evidence_paths = list(
                dict.fromkeys(
                    [
                        *(span.path for span in claim.evidence.spans),
                        *(proof.promoted_path for proof in claim.evidence.intake_proofs),
                    ]
                )
            )
            review = result.review_event
            review_reason = (
                f" Approved by {review.reviewer or 'an authorized reviewer'}"
                f" at {review.reviewed_at}."
                if review
                else " Approved by source governance policy."
            )
            evidence.append(
                ContextEvidence(
                    evidence_id=f"memory-claim:{claim.claim_id}",
                    case_id=case.case_id,
                    source_type="memory_claim",
                    source_path=f"memory-claim://{claim.claim_id}",
                    title=(f"Approved memory: {claim.entity.canonical_name} {claim.relation.type}"),
                    excerpt=(
                        f"{claim.entity.canonical_name} --{claim.relation.type}--> "
                        f"{relation_value}.{condition}"
                    ),
                    relevance_score=result.score,
                    reason=f"{result.reason}{review_reason}",
                    memory_claim_id=claim.claim_id,
                    governance_status=result.effective_status,
                    reviewed_by=review.reviewer if review else None,
                    reviewed_at=review.reviewed_at if review else None,
                    evidence_paths=evidence_paths,
                )
            )
        return evidence, batch.warnings

    def generate_impact_map(self, case_id: str) -> list[ImpactItem]:
        snapshot = self._ensure_analyzed(case_id)
        return snapshot.impact_items

    def generate_questions(
        self, case_id: str, *, role: str | None = None
    ) -> list[ClarificationQuestion]:
        snapshot = self._ensure_analyzed(case_id)
        if role is None:
            return snapshot.questions
        normalized = role.upper()
        return [question for question in snapshot.questions if question.target_role == normalized]

    def answer_question(
        self,
        case_id: str,
        question_id: str,
        answer: str,
        *,
        answered_by: str | None = None,
    ) -> ClarificationQuestion:
        snapshot = self._ensure_analyzed(case_id)
        answer_text = answer.strip()
        if not answer_text:
            raise ValueError("Clarification answer cannot be empty.")
        updated_question: ClarificationQuestion | None = None
        now = datetime.now(UTC).isoformat()
        questions: list[ClarificationQuestion] = []
        for question in snapshot.questions:
            if question.question_id == question_id:
                updated_question = question.model_copy(
                    update={
                        "status": "answered",
                        "answer": answer_text,
                        "answered_by": answered_by,
                        "answered_at": now,
                        "waived_reason": None,
                        "waived_by": None,
                        "waived_at": None,
                    }
                )
                questions.append(updated_question)
            else:
                questions.append(question)
        if updated_question is None:
            raise NotFoundError(f"Clarification question not found: {question_id}")
        snapshot.questions = questions
        snapshot.case.status = "questions_answered"
        snapshot.case.updated_at = now
        snapshot.jira_readiness = self._jira_readiness(snapshot)
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"question-answer-{uuid4().hex[:12]}",
            use_case="requirement_question_answer",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={
                "case_id": case_id,
                "question_id": question_id,
                "answer": answer_text,
                "answered_by": answered_by,
            },
            retrieved_source_paths=updated_question.related_sources,
            model_provider="human",
            model_name="clarification-answer-v1",
            output_path="sqlite:requirement_cases",
            status="answered",
            warnings=[],
        )
        return updated_question

    def waive_question(
        self,
        case_id: str,
        question_id: str,
        reason: str,
        *,
        waived_by: str | None = None,
    ) -> ClarificationQuestion:
        snapshot = self._ensure_analyzed(case_id)
        reason_text = reason.strip()
        if not reason_text:
            raise ValueError("Clarification waiver reason cannot be empty.")
        updated_question: ClarificationQuestion | None = None
        now = datetime.now(UTC).isoformat()
        questions: list[ClarificationQuestion] = []
        for question in snapshot.questions:
            if question.question_id == question_id:
                updated_question = question.model_copy(
                    update={
                        "status": "waived",
                        "answer": None,
                        "answered_by": None,
                        "answered_at": None,
                        "waived_reason": reason_text,
                        "waived_by": waived_by,
                        "waived_at": now,
                    }
                )
                questions.append(updated_question)
            else:
                questions.append(question)
        if updated_question is None:
            raise NotFoundError(f"Clarification question not found: {question_id}")
        snapshot.questions = questions
        snapshot.case.status = "questions_answered"
        snapshot.case.updated_at = now
        snapshot.jira_readiness = self._jira_readiness(snapshot)
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"question-waive-{uuid4().hex[:12]}",
            use_case="requirement_question_waive",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={
                "case_id": case_id,
                "question_id": question_id,
                "reason": reason_text,
                "waived_by": waived_by,
            },
            retrieved_source_paths=updated_question.related_sources,
            model_provider="human",
            model_name="clarification-waiver-v1",
            output_path="sqlite:requirement_cases",
            status="waived",
            warnings=[],
        )
        return updated_question

    def generate_role_view(self, case_id: str, role: str) -> RoleView:
        snapshot = self._ensure_analyzed(case_id)
        questions = self.generate_questions(case_id, role=role)
        sources = _evidence_source_paths(snapshot.evidence)
        question_lines = "\n".join(f"- {item.question}" for item in questions) or "- None"
        markdown = f"""# {role.upper()} View

## Request
{snapshot.case.raw_request}

## Relevant Questions
{question_lines}

## Sources Used
{_source_lines(sources)}
"""
        role_view = RoleView(
            case_id=snapshot.case.case_id,
            role=role.upper(),
            markdown=markdown,
            sources_used=sources,
        )
        snapshot.role_views = [
            item for item in snapshot.role_views if item.role != role_view.role
        ] + [role_view]
        snapshot.case.updated_at = datetime.now(UTC).isoformat()
        self.repository.save(snapshot)
        return role_view

    def generate_engineering_brief(self, case_id: str) -> EngineeringBrief:
        snapshot = self._ensure_analyzed(case_id)
        brief = self.brief_generator.generate(snapshot)
        output_path = self._case_artifact_dir(case_id) / "engineering-brief.md"
        output_path.write_text(brief.markdown, encoding="utf-8")
        snapshot.engineering_brief = brief
        snapshot.case.status = "brief_generated"
        snapshot.case.updated_at = datetime.now(UTC).isoformat()
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"brief-{uuid4().hex[:12]}",
            use_case="engineering_brief",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={"case_id": case_id},
            retrieved_source_paths=brief.sources_used,
            model_provider=getattr(self.brief_generator, "last_model_provider", "deterministic"),
            model_name=getattr(self.brief_generator, "last_model_name", "engineering-brief-v1"),
            output_path=display_path(output_path),
            status="success",
            warnings=brief.warnings,
        )
        from dream.context import ContextIntelligenceService

        ContextIntelligenceService(
            requirement_repository=self.repository,
            codebase_repository=self.codebase_repository,
            memory_repository=self.memory_claim_retriever.repository,
        ).prompt_for_case(case_id, target="engineering_brief")
        return brief

    def prepare_jira_draft_context(self, case_id: str) -> JiraDraftContext:
        snapshot = self._ensure_analyzed(case_id)
        context = self.jira_generator.prepare(snapshot)
        output_path = self._case_artifact_dir(case_id) / "jira-draft-context.md"
        output_path.write_text(
            "\n\n".join(
                [
                    "# Jira Draft Context",
                    "## Deterministic Draft",
                    context.deterministic_markdown,
                    "## LLM Prompt",
                    context.prompt,
                ]
            ),
            encoding="utf-8",
        )
        self.audit_logger.log_generation(
            run_id=f"jira-context-{uuid4().hex[:12]}",
            use_case="jira_draft_context",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={
                "case_id": case_id,
                "prompt_char_count": context.prompt_char_count,
                "deterministic_char_count": context.deterministic_char_count,
            },
            retrieved_source_paths=context.sources_used,
            model_provider="deterministic",
            model_name="jira-draft-context-v1",
            output_path=display_path(output_path),
            status="success",
            warnings=context.warnings,
        )
        return context

    def generate_jira_draft(self, case_id: str) -> JiraDraft:
        snapshot = self._ensure_analyzed(case_id)
        jira = self.jira_generator.generate(snapshot)
        readiness = self._jira_readiness(snapshot, jira_draft_exists=True)
        if not readiness.ready:
            jira.warnings = list(dict.fromkeys([*jira.warnings, *readiness.blocking_reasons]))
        output_path = self._case_artifact_dir(case_id) / "jira-draft.md"
        output_path.write_text(jira.markdown, encoding="utf-8")
        snapshot.jira_draft = jira
        snapshot.jira_readiness = readiness
        snapshot.case.status = readiness.status
        snapshot.case.updated_at = datetime.now(UTC).isoformat()
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"jira-{uuid4().hex[:12]}",
            use_case="jira_draft",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={"case_id": case_id},
            retrieved_source_paths=jira.sources_used,
            model_provider=getattr(self.jira_generator, "last_model_provider", "deterministic"),
            model_name=getattr(self.jira_generator, "last_model_name", "jira-draft-v1"),
            output_path=display_path(output_path),
            status=readiness.status,
            warnings=jira.warnings,
        )
        from dream.context import ContextIntelligenceService

        ContextIntelligenceService(
            requirement_repository=self.repository,
            codebase_repository=self.codebase_repository,
            memory_repository=self.memory_claim_retriever.repository,
        ).prompt_for_case(case_id, target="jira_draft")
        return jira

    def jira_readiness(self, case_id: str) -> JiraReadiness:
        snapshot = self._ensure_analyzed(case_id)
        readiness = self._jira_readiness(snapshot)
        snapshot.jira_readiness = readiness
        snapshot.case.status = readiness.status
        snapshot.case.updated_at = datetime.now(UTC).isoformat()
        self.repository.save(snapshot)
        self.audit_logger.log_generation(
            run_id=f"jira-readiness-{uuid4().hex[:12]}",
            use_case="jira_readiness_check",
            team_id=snapshot.case.team_id,
            case_id=snapshot.case.case_id,
            input_payload={"case_id": case_id},
            retrieved_source_paths=_evidence_source_paths(snapshot.evidence),
            model_provider="deterministic",
            model_name="jira-readiness-v1",
            output_path="sqlite:requirement_cases",
            status=readiness.status,
            warnings=readiness.blocking_reasons,
        )
        return readiness

    def get_case(self, case_id: str) -> RequirementCaseSnapshot:
        return self.repository.get(case_id)

    def list_cases(self) -> list[RequirementCaseSnapshot]:
        return self.repository.list()

    def _ensure_analyzed(self, case_id: str) -> RequirementCaseSnapshot:
        snapshot = self.repository.get(case_id)
        if not snapshot.evidence and snapshot.case.status == "created":
            return self.analyze_case(case_id)
        return snapshot

    def _default_repo_name(self, team_id: str) -> str | None:
        repo_names = self.codebase_repository.list_repo_names(team_id)
        return repo_names[0] if repo_names else None

    @staticmethod
    def _jira_readiness(
        snapshot: RequirementCaseSnapshot,
        *,
        jira_draft_exists: bool | None = None,
    ) -> JiraReadiness:
        open_questions = [question for question in snapshot.questions if question.status == "open"]
        answered_questions = [
            question for question in snapshot.questions if question.status == "answered"
        ]
        waived_questions = [
            question for question in snapshot.questions if question.status == "waived"
        ]
        draft_exists = (
            snapshot.jira_draft is not None if jira_draft_exists is None else jira_draft_exists
        )
        blocking: list[str] = []
        if not snapshot.evidence:
            blocking.append("No retrieved evidence is attached to the requirement case.")
        if not snapshot.impact_items:
            blocking.append("No impact map has been generated.")
        if open_questions:
            blocking.append(
                f"{len(open_questions)} clarification question(s) still need human answers."
            )
        if not draft_exists:
            blocking.append("Jira draft has not been generated yet.")
        ready = not blocking
        recommendations = []
        if open_questions:
            recommendations.append(
                "Answer or explicitly waive open questions before Jira approval."
            )
        if not snapshot.evidence:
            recommendations.append("Run requirement analysis after knowledge/codebase indexing.")
        if not draft_exists:
            recommendations.append("Generate the Jira draft after answering questions.")
        status = "jira_ready_draft" if ready else "jira_draft_needs_answers"
        return JiraReadiness(
            case_id=snapshot.case.case_id,
            ready=ready,
            status=status,
            answered_questions=len(answered_questions),
            waived_questions=len(waived_questions),
            open_questions=len(open_questions),
            evidence_items=len(snapshot.evidence),
            impact_items=len(snapshot.impact_items),
            jira_draft_exists=draft_exists,
            blocking_reasons=blocking,
            recommendations=recommendations,
        )

    @staticmethod
    def _with_case_id(case_id: str, evidence: list[ContextEvidence]) -> list[ContextEvidence]:
        return [item.model_copy(update={"case_id": case_id}) for item in evidence]

    @staticmethod
    def _title(raw_request: str) -> str:
        words = raw_request.strip().split()
        title = " ".join(words[:10])
        return title.rstrip(".") or "Untitled Requirement Case"

    @staticmethod
    def _case_artifact_dir(case_id: str) -> Path:
        path = resolve_artifact_path(Path("requirement-cases") / case_id)
        path.mkdir(parents=True, exist_ok=True)
        return path


def _source_lines(sources: list[str]) -> str:
    return "\n".join(f"- {source}" for source in sources) or "- No sources used."


def _evidence_source_paths(evidence: list[ContextEvidence]) -> list[str]:
    return sorted({path for item in evidence for path in item.provenance_paths()})
