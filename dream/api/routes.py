# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.core.errors import DreamError
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationRequest, EvaluationResult
from dream.evals.repository import EvaluationRepository
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRetriever
from dream.llm import MockLLMProvider, OpenAICompatibleProvider
from dream.memory import MemoryDistillationEvaluator, MemoryDistillationService
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.requirements import (
    RequirementDraftGenerator,
    RequirementDraftRequest,
    RequirementDraftResponse,
)
from dream.review import PRReviewAssistant, PRReviewRequest, PRReviewResponse
from dream.testgen import JTestGenAdapter, MockTestGenProvider, TestGenRequest, TestGenResult

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


class TestGenRunRequest(TestGenRequest):
    provider: str = Field(default="mock")


class CodebaseIndexRequest(BaseModel):
    team_id: str
    repo_path: str
    repo_name: str | None = None


class EvidenceGraphBuildRequest(BaseModel):
    team_id: str
    repo_name: str | None = None


class MemoryScanRequest(BaseModel):
    team_id: str
    repo_path: str
    repo_name: str | None = None


class MemoryEvalRequest(BaseModel):
    team_id: str
    scan_id: str = "latest"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/requirements/draft", response_model=RequirementDraftResponse)
def draft_requirement(request: RequirementDraftRequest) -> RequirementDraftResponse:
    try:
        return RequirementDraftGenerator(
            llm_provider=_llm_provider(request.llm_provider)
        ).draft(request)
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review/pr", response_model=PRReviewResponse)
def review_pr(request: PRReviewRequest) -> PRReviewResponse:
    try:
        return PRReviewAssistant(llm_provider=_llm_provider(request.llm_provider)).review(
            request
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/codebase/index")
def index_codebase(request: CodebaseIndexRequest) -> dict[str, object]:
    try:
        index = CodebaseIndexer().index(
            team_id=request.team_id,
            repo_path=request.repo_path,
            repo_name=request.repo_name,
        )
        return index.model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/codebase/search")
def search_codebase(
    team_id: str,
    repo_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, object]]:
    results = CodebaseRetriever().search(
        team_id=team_id,
        repo_name=repo_name,
        query=query,
        top_k=top_k,
    )
    return [result.model_dump() for result in results]


@router.get("/codebase/concepts")
def list_codebase_concepts(team_id: str, repo_name: str) -> list[dict[str, object]]:
    try:
        index = CodebaseIndexRepository().load(team_id, repo_name)
        return [concept.model_dump() for concept in index.concepts]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/codebase/files")
def list_codebase_files(team_id: str, repo_name: str) -> list[dict[str, object]]:
    try:
        index = CodebaseIndexRepository().load(team_id, repo_name)
        return [file_node.model_dump() for file_node in index.files]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/graph/build")
def build_evidence_graph(request: EvidenceGraphBuildRequest) -> dict[str, object]:
    try:
        return EvidenceGraphBuilder().build(
            team_id=request.team_id,
            repo_name=request.repo_name,
        ).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/graph/search")
def search_evidence_graph(
    team_id: str,
    query: str,
    repo_name: str | None = None,
    top_k: int = 8,
) -> list[dict[str, object]]:
    results = EvidenceGraphRetriever().search(
        team_id=team_id,
        repo_name=repo_name,
        query=query,
        top_k=top_k,
    )
    return [result.model_dump() for result in results]


@router.get("/graph/explain")
def explain_evidence_graph(
    team_id: str,
    concept: str,
    repo_name: str | None = None,
) -> dict[str, object]:
    return EvidenceGraphRetriever().explain(
        team_id=team_id,
        repo_name=repo_name,
        query=concept,
    ).model_dump()


@router.get("/graph/neighbors")
def get_evidence_graph_neighbors(
    team_id: str,
    node: str,
    repo_name: str | None = None,
) -> dict[str, object]:
    return EvidenceGraphRetriever().neighbors(
        team_id=team_id,
        repo_name=repo_name,
        node=node,
    ).model_dump()


@router.post("/memory/scan")
def scan_memory(request: MemoryScanRequest) -> dict[str, object]:
    try:
        return MemoryDistillationService().scan(
            team_id=request.team_id,
            repo_path=request.repo_path,
            repo_name=request.repo_name,
        ).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/memory/scans/latest")
def get_latest_memory_scan(team_id: str) -> dict[str, object]:
    scan = MemoryDistillationRepository().try_load_latest_scan(team_id)
    if scan is None:
        raise HTTPException(
            status_code=404,
            detail=f"Memory scan not found: {team_id}/latest",
        )
    return scan.model_dump()


@router.get("/memory/diff")
def diff_memory(team_id: str, scan_id: str = "latest") -> dict[str, object]:
    try:
        markdown = MemoryDistillationService().diff_markdown(
            team_id=team_id,
            scan_id=scan_id,
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"team_id": team_id, "scan_id": scan_id, "markdown": markdown}


@router.post("/memory/eval")
def eval_memory(request: MemoryEvalRequest) -> dict[str, object]:
    try:
        return MemoryDistillationEvaluator().evaluate(
            team_id=request.team_id,
            scan_id=request.scan_id,
        ).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/requirement-cases")
def create_requirement_case(request: RequirementCaseCreateRequest) -> dict[str, object]:
    try:
        return RequirementCaseService().create_case(request).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/requirement-cases/{case_id}/analyze")
def analyze_requirement_case(case_id: str) -> dict[str, object]:
    try:
        return RequirementCaseService().analyze_case(case_id).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases")
def list_requirement_cases() -> list[dict[str, object]]:
    return [snapshot.model_dump() for snapshot in RequirementCaseService().list_cases()]


@router.get("/requirement-cases/{case_id}")
def get_requirement_case(case_id: str) -> dict[str, object]:
    try:
        return RequirementCaseService().get_case(case_id).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/impact-map")
def get_requirement_case_impact(case_id: str) -> list[dict[str, object]]:
    try:
        items = RequirementCaseService().generate_impact_map(case_id)
        return [item.model_dump() for item in items]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/questions")
def get_requirement_case_questions(
    case_id: str, role: str | None = None
) -> list[dict[str, object]]:
    try:
        questions = RequirementCaseService().generate_questions(case_id, role=role)
        return [question.model_dump() for question in questions]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/brief")
def get_requirement_case_brief(
    case_id: str,
    llm_provider: str = "deterministic",
) -> dict[str, object]:
    try:
        return RequirementCaseService(
            llm_provider=_optional_llm_provider(llm_provider)
        ).generate_engineering_brief(case_id).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/jira-draft")
def get_requirement_case_jira_draft(
    case_id: str,
    llm_provider: str = "deterministic",
) -> dict[str, object]:
    try:
        return RequirementCaseService(
            llm_provider=_optional_llm_provider(llm_provider)
        ).generate_jira_draft(case_id).model_dump()
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/testgen/run", response_model=TestGenResult)
def run_testgen(request: TestGenRunRequest) -> TestGenResult:
    provider = _testgen_provider(request.provider)
    try:
        return provider.run(TestGenRequest.model_validate(request.model_dump()))
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/audit/runs")
def list_audit_runs() -> list[dict[str, object]]:
    return [record.model_dump() for record in AuditRepository().list_audit_records()]


@router.get("/audit/runs/{run_id}")
def get_audit_run(run_id: str) -> dict[str, object]:
    record = AuditRepository().get_audit_record(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Audit run not found: {run_id}")
    return record.model_dump()


@router.post("/eval/run", response_model=EvaluationResult)
def run_evaluation(request: EvaluationRequest) -> EvaluationResult:
    try:
        return EvaluationAgent().evaluate(request)
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eval/runs")
def list_evaluation_runs() -> list[dict[str, object]]:
    return [scorecard.model_dump() for scorecard in EvaluationRepository().list()]


@router.get("/eval/runs/{evaluation_id}")
def get_evaluation_run(evaluation_id: str) -> dict[str, object]:
    scorecard = EvaluationRepository().get(evaluation_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail=f"Evaluation not found: {evaluation_id}")
    return scorecard.model_dump()


def _testgen_provider(provider: str) -> MockTestGenProvider | JTestGenAdapter:
    if provider == "mock":
        return MockTestGenProvider()
    if provider == "jtestgen":
        return JTestGenAdapter()
    raise HTTPException(status_code=400, detail=f"Unsupported testgen provider: {provider}")


def _llm_provider(provider: str) -> MockLLMProvider | OpenAICompatibleProvider:
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")


def _optional_llm_provider(
    provider: str,
) -> MockLLMProvider | OpenAICompatibleProvider | None:
    if provider == "deterministic":
        return None
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")
