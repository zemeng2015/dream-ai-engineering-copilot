# SPDX-License-Identifier: Apache-2.0

import json
import os
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from dream.api.security import (
    get_access_context,
    identity_boundary,
    private_acl_route,
    private_anonymous_route,
)
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.config import resolve_config
from dream.context import ContextEvaluationService, ContextIntelligenceService
from dream.core.errors import (
    DreamError,
    NotFoundError,
    PathTraversalError,
    ProviderConfigurationError,
)
from dream.core.paths import resolve_project_path
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationJudgeRequest, EvaluationRequest, EvaluationResult
from dream.evals.rating import HumanRatingService
from dream.evals.repository import EvaluationRepository
from dream.extensions import build_llm_provider
from dream.extensions.models import LLMProvider
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRetriever
from dream.intake import DraftMetadataUpdate, KnowledgeIntakeService, ReviewDecision
from dream.llm import MockLLMProvider, OpenAICompatibleProvider, QwenCloudProvider
from dream.llm.egress import require_private_provider_selector
from dream.memory import (
    MemoryClaimRetriever,
    MemoryDistillationEvaluator,
    MemoryDistillationService,
)
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.requirements import (
    RequirementDraftGenerator,
    RequirementDraftRequest,
    RequirementDraftResponse,
)
from dream.review import PRReviewAssistant, PRReviewRequest, PRReviewResponse
from dream.security import AccessContext, DefaultAccessPolicy
from dream.testgen import JTestGenAdapter, MockTestGenProvider, TestGenRequest, TestGenResult

router = APIRouter(dependencies=[Depends(identity_boundary)])
AccessContextDep = Annotated[AccessContext, Depends(get_access_context)]
_PUBLIC_QWEN_REQUEST_TIMES: deque[float] = deque()
_PUBLIC_QWEN_RATE_LOCK = Lock()


class HealthResponse(BaseModel):
    status: str
    service: str = "dream-memoryagent-api"
    track: str = "Track 1: MemoryAgent"
    deployment_target: str = "local"
    alibaba_cloud_region: str | None = None
    alibaba_cloud_service: str | None = None
    llm_provider: str
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key_configured: bool = False
    proof_file: str = "deploy/alibaba/serverless-devs-runtime.yaml"


class QwenCloudShowcaseRuntime(BaseModel):
    status: str
    service: str
    track: str
    deployment_target: str
    alibaba_cloud_region: str | None = None
    alibaba_cloud_service: str | None = None
    llm_provider: str
    llm_model: str | None = None
    llm_api_key_configured: bool
    proof_file: str
    qwen_cloud_ready: bool
    alibaba_runtime_ready: bool
    live_backend_ready: bool


class QwenCloudShowcaseStep(BaseModel):
    order: str
    title: str
    route: str
    outcome: str
    evidence_paths: list[str]


class QwenCloudShowcaseEvidenceItem(BaseModel):
    name: str
    state: str
    proof_paths: list[str]


class QwenCloudShowcaseScorecard(BaseModel):
    weighted_current_evidence_ready: int
    weighted_static_evidence_ready: int = 100
    weighted_total: int = 100
    live_backend_points: int
    public_video_points: int = 0
    missing_external_inputs: list[str]


class QwenCloudShowcaseBenchmark(BaseModel):
    status: str
    run_id: str | None = None
    provider: str | None = None
    model: str | None = None
    case_count: int = 0
    baseline_score: float = 0
    dream_score: float = 0
    score_delta: float = 0
    median_delta: float = 0
    exact_paired_permutation_p: float | None = None
    dream_wins: int = 0
    exact_retrieval_recall_at_12: float = 0
    report_path: str | None = None
    limitations: list[str] = Field(default_factory=list)


class QwenCloudShowcaseResponse(BaseModel):
    generated_at: str
    project_title: str
    track: str
    elevator_pitch: str
    runtime: QwenCloudShowcaseRuntime
    judge_flow: list[QwenCloudShowcaseStep]
    evidence: list[QwenCloudShowcaseEvidenceItem]
    benchmark: QwenCloudShowcaseBenchmark
    scorecard: QwenCloudShowcaseScorecard


class TestGenRunRequest(TestGenRequest):
    provider: str = Field(default="mock")


class CodebaseIndexRequest(BaseModel):
    team_id: str
    repo_path: str
    repo_name: str | None = None


class CodebaseIndexArtifactResponse(BaseModel):
    index_path: str
    index: dict[str, object]


class CodebaseFileContentResponse(BaseModel):
    path: str
    language: str
    role: str
    size_bytes: int
    line_count: int
    content: str


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


class MemoryReviewRequest(BaseModel):
    team_id: str
    claim_id: str
    status: str
    reviewer: str | None = None
    reason: str | None = None
    scan_id: str = "latest"


class MemoryConflictResolveRequest(BaseModel):
    team_id: str
    conflict_id: str
    winning_claim_id: str
    action: str = "approve_winner_reject_other"
    reviewer: str | None = None
    reason: str | None = None
    scan_id: str = "latest"


class IntakeUploadRequest(BaseModel):
    team_id: str
    file_path: str
    document_type: str = "architecture"
    title: str | None = None


class IntakeReviewRequest(BaseModel):
    status: str
    reviewer: str | None = None
    notes: str | None = None


class RetrievalEvalRequest(BaseModel):
    case_id: str
    profile_id: str


class HumanRatingRequest(BaseModel):
    usefulness_score: int = Field(ge=1, le=5)
    correctness_score: int = Field(ge=1, le=5)
    comments: str = Field(min_length=1)


class RequirementQuestionAnswerRequest(BaseModel):
    answer: str
    answered_by: str | None = None


class RequirementQuestionWaiveRequest(BaseModel):
    reason: str
    waived_by: str | None = None


def _authorized_codebase_index(
    team_id: str,
    repo_name: str,
    access_context: AccessContext,
):
    index = CodebaseIndexRepository().load(team_id, repo_name)
    DefaultAccessPolicy().require(
        context=access_context,
        team_id=team_id,
        action="retrieve",
        resource_access=index.access,
        resource_id=index.repo_id,
    )
    return index


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    config = resolve_config()
    deployment_target = "local"
    alibaba_service = os.getenv("ALIBABA_CLOUD_SERVICE")
    if config.llm.provider == "qwen-cloud" and (
        alibaba_service or os.getenv("ALIBABA_CLOUD_REGION")
    ):
        deployment_target = "Alibaba Cloud " + (alibaba_service or "Function Compute")
    return HealthResponse(
        status="ok",
        deployment_target=deployment_target,
        alibaba_cloud_region=os.getenv("ALIBABA_CLOUD_REGION"),
        alibaba_cloud_service=alibaba_service,
        llm_provider=config.llm.provider,
        llm_model=config.llm.model,
        llm_base_url=config.llm.base_url,
        llm_api_key_configured=config.llm.api_key_configured,
        proof_file=os.getenv("ALIBABA_CLOUD_PROOF_FILE")
        or "deploy/alibaba/serverless-devs-runtime.yaml",
    )


@router.get("/health/live")
@private_anonymous_route
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/qwencloud/showcase", response_model=QwenCloudShowcaseResponse)
def qwencloud_showcase() -> QwenCloudShowcaseResponse:
    health_payload = health()
    proof_file_ready = health_payload.proof_file == "deploy/alibaba/serverless-devs-runtime.yaml"
    qwen_cloud_ready = (
        health_payload.status == "ok"
        and health_payload.track == "Track 1: MemoryAgent"
        and health_payload.llm_provider == "qwen-cloud"
        and health_payload.llm_api_key_configured
        and proof_file_ready
    )
    alibaba_runtime_ready = (
        "Alibaba Cloud Function Compute" in health_payload.deployment_target and proof_file_ready
    )
    live_backend_ready = qwen_cloud_ready and alibaba_runtime_ready
    live_backend_points = 30 if live_backend_ready else 0
    missing_external_inputs = ["public_demo_video_url"]
    if not live_backend_ready:
        missing_external_inputs.insert(0, "deployed_backend_url")

    return QwenCloudShowcaseResponse(
        generated_at=datetime.now(UTC).isoformat(),
        project_title="DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence",
        track="Track 1: MemoryAgent",
        elevator_pitch=(
            "DREAM turns tickets, code, incidents, runbooks, and review history into "
            "auditable memory so Qwen Cloud can draft and review engineering work from "
            "source-backed context instead of one-shot prompts."
        ),
        runtime=QwenCloudShowcaseRuntime(
            status=health_payload.status,
            service=health_payload.service,
            track=health_payload.track,
            deployment_target=health_payload.deployment_target,
            alibaba_cloud_region=health_payload.alibaba_cloud_region,
            alibaba_cloud_service=health_payload.alibaba_cloud_service,
            llm_provider=health_payload.llm_provider,
            llm_model=health_payload.llm_model,
            llm_api_key_configured=health_payload.llm_api_key_configured,
            proof_file=health_payload.proof_file,
            qwen_cloud_ready=qwen_cloud_ready,
            alibaba_runtime_ready=alibaba_runtime_ready,
            live_backend_ready=live_backend_ready,
        ),
        judge_flow=[
            QwenCloudShowcaseStep(
                order="01",
                title="Approve source-backed memory",
                route="/memory",
                outcome=(
                    "Review source claims, conflicts, section proofs, and promoted memory "
                    "before generation."
                ),
                evidence_paths=[
                    "dream/memory/distiller.py",
                    "dream/memory/repository.py",
                    "docs/memory-distillation.md",
                ],
            ),
            QwenCloudShowcaseStep(
                order="02",
                title="Generate a requirement case",
                route="/requirements",
                outcome=(
                    "Turn a rough engineering request into questions, impact areas, an "
                    "engineering brief, and Jira draft."
                ),
                evidence_paths=[
                    "dream/requirement_cases/service.py",
                    "dream/requirements/generator.py",
                    "tests/test_requirement_cases.py",
                ],
            ),
            QwenCloudShowcaseStep(
                order="03",
                title="Inspect the context trail",
                route="/context/case_async_status",
                outcome=(
                    "Show retrieval paths, graph expansion, memory claims, and prompt "
                    "preview before the model writes."
                ),
                evidence_paths=[
                    "dream/context/service.py",
                    "docs/context-intelligence-layer.md",
                    "tests/test_context_intelligence.py",
                ],
            ),
            QwenCloudShowcaseStep(
                order="04",
                title="Bind codebase evidence",
                route="/codebase",
                outcome=(
                    "Map the request to backend, frontend, tests, incidents, historical "
                    "PRs, and Jira sources."
                ),
                evidence_paths=[
                    "dream/codebase/indexer.py",
                    "dream/graph/builder.py",
                    "tests/test_codebase_memory.py",
                ],
            ),
            QwenCloudShowcaseStep(
                order="05",
                title="Close with audit and eval",
                route="/audit",
                outcome=(
                    "Prove outputs are reviewable through scorecards, warnings, source "
                    "coverage, and human ratings."
                ),
                evidence_paths=[
                    "dream/evals/evaluator.py",
                    "dream/audit/logger.py",
                    "tests/test_audit_logger.py",
                ],
            ),
        ],
        evidence=[
            QwenCloudShowcaseEvidenceItem(
                name="Qwen Cloud provider",
                state="live" if qwen_cloud_ready else "configured",
                proof_paths=[
                    "dream/llm/qwen_cloud.py",
                    "examples/config/dream.qwen.yaml",
                    "tests/test_qwen_cloud_provider.py",
                ],
            ),
            QwenCloudShowcaseEvidenceItem(
                name="Alibaba Function Compute deployment",
                state="live" if alibaba_runtime_ready else "packaged",
                proof_paths=[
                    "deploy/alibaba/serverless-devs-runtime.yaml",
                    "scripts/qwencloud-build-fc-code-package.ps1",
                    "scripts/qwencloud-alibaba-runtime-release.ps1",
                ],
            ),
            QwenCloudShowcaseEvidenceItem(
                name="Judge-facing demo route",
                state="ready",
                proof_paths=[
                    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts",
                    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.html",
                    "docs/qwencloud-demo-video-script.md",
                ],
            ),
            QwenCloudShowcaseEvidenceItem(
                name="Paired Qwen memory benchmark",
                state="measured",
                proof_paths=[
                    "docs/assets/qwen-memory-ab-benchmark-summary.json",
                    "scripts/qwencloud_memory_ab_benchmark.py",
                    "tests/test_qwencloud_memory_ab_benchmark.py",
                ],
            ),
        ],
        benchmark=_qwen_benchmark_summary(),
        scorecard=QwenCloudShowcaseScorecard(
            weighted_current_evidence_ready=55 + live_backend_points,
            live_backend_points=live_backend_points,
            missing_external_inputs=missing_external_inputs,
        ),
    )


def _qwen_benchmark_summary() -> QwenCloudShowcaseBenchmark:
    path_value = os.getenv(
        "QWEN_BENCHMARK_SUMMARY_FILE",
        "docs/assets/qwen-memory-ab-benchmark-summary.json",
    )
    path = resolve_project_path(path_value)
    if not path.is_file():
        return QwenCloudShowcaseBenchmark(
            status="missing",
            limitations=["Benchmark summary file is not packaged."],
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return QwenCloudShowcaseBenchmark(
            status="ready",
            run_id=str(data["run_id"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            case_count=int(data["case_count"]),
            baseline_score=float(data["baseline_mean"]),
            dream_score=float(data["dream_mean"]),
            score_delta=float(data["mean_delta"]),
            median_delta=float(data["median_delta"]),
            exact_paired_permutation_p=float(data["exact_paired_permutation_p"]),
            dream_wins=int(data["dream_wins"]),
            exact_retrieval_recall_at_12=float(data["exact_retrieval_recall_at_12"]),
            report_path=str(data["report_path"]),
            limitations=[str(item) for item in data.get("limitations", [])],
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return QwenCloudShowcaseBenchmark(
            status="invalid",
            limitations=["Benchmark summary file failed schema validation."],
        )


@router.post("/requirements/draft", response_model=RequirementDraftResponse)
def draft_requirement(request: RequirementDraftRequest) -> RequirementDraftResponse:
    try:
        return RequirementDraftGenerator(llm_provider=_llm_provider(request.llm_provider)).draft(
            request
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review/pr", response_model=PRReviewResponse)
@private_acl_route
def review_pr(
    request: PRReviewRequest,
    access_context: AccessContextDep,
) -> PRReviewResponse:
    try:
        return PRReviewAssistant(llm_provider=_llm_provider(request.llm_provider)).review(
            request,
            access_context=access_context,
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


@router.get("/codebase/index", response_model=CodebaseIndexArtifactResponse)
def get_codebase_index(team_id: str, repo_name: str) -> CodebaseIndexArtifactResponse:
    try:
        repository = CodebaseIndexRepository()
        index = repository.load(team_id, repo_name)
        return CodebaseIndexArtifactResponse(
            index_path=repository.display_index_path(team_id, repo_name),
            index=index.model_dump(),
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/codebase/search")
@private_acl_route
def search_codebase(
    team_id: str,
    repo_name: str,
    query: str,
    access_context: AccessContextDep,
    top_k: int = 5,
) -> list[dict[str, object]]:
    results = CodebaseRetriever().search(
        team_id=team_id,
        repo_name=repo_name,
        query=query,
        top_k=top_k,
        access_context=access_context,
    )
    return [result.model_dump() for result in results]


@router.get("/codebase/concepts")
@private_acl_route
def list_codebase_concepts(
    team_id: str,
    repo_name: str,
    access_context: AccessContextDep,
) -> list[dict[str, object]]:
    try:
        index = _authorized_codebase_index(team_id, repo_name, access_context)
        policy = DefaultAccessPolicy()
        return [
            concept.model_dump()
            for concept in index.concepts
            if policy.decide(
                context=access_context,
                team_id=team_id,
                action="retrieve",
                resource_access=concept.access,
                resource_id=f"concept:{concept.concept}",
            ).allowed
        ]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/codebase/files")
@private_acl_route
def list_codebase_files(
    team_id: str,
    repo_name: str,
    access_context: AccessContextDep,
) -> list[dict[str, object]]:
    try:
        index = _authorized_codebase_index(team_id, repo_name, access_context)
        policy = DefaultAccessPolicy()
        return [
            file_node.model_dump()
            for file_node in index.files
            if policy.decide(
                context=access_context,
                team_id=team_id,
                action="retrieve",
                resource_access=file_node.access,
                resource_id=file_node.file_id,
            ).allowed
        ]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/codebase/file-content", response_model=CodebaseFileContentResponse)
@private_acl_route
def get_codebase_file_content(
    team_id: str,
    repo_name: str,
    file_path: str,
    access_context: AccessContextDep,
) -> CodebaseFileContentResponse:
    try:
        index = _authorized_codebase_index(team_id, repo_name, access_context)
        file_node = next((item for item in index.files if item.path == file_path), None)
        if file_node is None:
            raise NotFoundError(f"File is not present in the codebase index: {file_path}")
        DefaultAccessPolicy().require(
            context=access_context,
            team_id=team_id,
            action="retrieve",
            resource_access=file_node.access,
            resource_id=file_node.file_id,
        )

        repo_root = resolve_project_path(index.repo_path, must_exist=True).resolve()
        target_path = (repo_root / file_node.path).resolve()
        if not target_path.is_relative_to(repo_root):
            raise PathTraversalError(f"File path escapes repo root: {file_path}")
        if not target_path.is_file():
            raise NotFoundError(f"Indexed file does not exist on disk: {file_path}")

        return CodebaseFileContentResponse(
            path=file_node.path,
            language=file_node.language,
            role=file_node.role,
            size_bytes=file_node.size_bytes,
            line_count=file_node.line_count,
            content=target_path.read_text(encoding="utf-8", errors="replace"),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/graph/build")
def build_evidence_graph(request: EvidenceGraphBuildRequest) -> dict[str, object]:
    try:
        return (
            EvidenceGraphBuilder()
            .build(
                team_id=request.team_id,
                repo_name=request.repo_name,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/graph/search")
@private_acl_route
def search_evidence_graph(
    team_id: str,
    query: str,
    access_context: AccessContextDep,
    repo_name: str | None = None,
    top_k: int = 8,
) -> list[dict[str, object]]:
    results = EvidenceGraphRetriever().search(
        team_id=team_id,
        repo_name=repo_name,
        query=query,
        top_k=top_k,
        access_context=access_context,
    )
    return [result.model_dump() for result in results]


@router.get("/graph/explain")
@private_acl_route
def explain_evidence_graph(
    team_id: str,
    concept: str,
    access_context: AccessContextDep,
    repo_name: str | None = None,
) -> dict[str, object]:
    return (
        EvidenceGraphRetriever()
        .explain(
            team_id=team_id,
            repo_name=repo_name,
            query=concept,
            access_context=access_context,
        )
        .model_dump()
    )


@router.get("/graph/neighbors")
@private_acl_route
def get_evidence_graph_neighbors(
    team_id: str,
    node: str,
    access_context: AccessContextDep,
    repo_name: str | None = None,
) -> dict[str, object]:
    return (
        EvidenceGraphRetriever()
        .neighbors(
            team_id=team_id,
            repo_name=repo_name,
            node=node,
            access_context=access_context,
        )
        .model_dump()
    )


@router.post("/intake/documents")
def upload_intake_document(request: IntakeUploadRequest) -> dict[str, object]:
    try:
        return (
            KnowledgeIntakeService()
            .upload_local_file(
                team_id=request.team_id,
                file_path=request.file_path,
                document_type=request.document_type,
                title=request.title,
            )
            .model_dump()
        )
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/documents/upload")
async def upload_intake_document_file(
    team_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    document_type: Annotated[str, Form()] = "architecture",
    title: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    try:
        content = await file.read()
        return (
            KnowledgeIntakeService()
            .upload_file_content(
                team_id=team_id,
                filename=file.filename or "uploaded-source",
                content=content,
                document_type=document_type,
                title=title,
            )
            .model_dump()
        )
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@router.get("/intake/documents")
def list_intake_documents() -> list[dict[str, object]]:
    return [item.model_dump() for item in KnowledgeIntakeService().repository.list_documents()]


@router.get("/intake/documents/{document_id}")
def get_intake_document(document_id: str) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().repository.get_document(document_id).model_dump()
    except OSError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/intake/documents/{document_id}/detail")
def get_intake_document_detail(document_id: str) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().get_document_detail(document_id).model_dump()
    except OSError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/intake/documents/{document_id}/parse")
def parse_intake_document(document_id: str) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().parse_document(document_id).model_dump()
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/intake/drafts/{draft_id}")
def get_intake_draft(draft_id: str) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().repository.get_draft(draft_id).model_dump()
    except OSError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/intake/drafts/{draft_id}/review-events")
def list_intake_draft_review_events(draft_id: str) -> list[dict[str, object]]:
    try:
        service = KnowledgeIntakeService()
        service.repository.get_draft(draft_id)
        return [event.model_dump() for event in service.repository.list_review_events(draft_id)]
    except OSError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/intake/drafts/{draft_id}/metadata")
def update_intake_draft_metadata(
    draft_id: str,
    request: DraftMetadataUpdate,
) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().update_draft_metadata(draft_id, request).model_dump()
    except (DreamError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/drafts/{draft_id}/review")
def review_intake_draft(draft_id: str, request: IntakeReviewRequest) -> dict[str, object]:
    try:
        return (
            KnowledgeIntakeService()
            .review_draft(
                draft_id,
                ReviewDecision(
                    status=request.status,
                    reviewer=request.reviewer,
                    notes=request.notes,
                ),
            )
            .model_dump()
        )
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intake/drafts/{draft_id}/promote")
def promote_intake_draft(draft_id: str) -> dict[str, object]:
    try:
        return KnowledgeIntakeService().promote_draft(draft_id).model_dump()
    except (DreamError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/context/trails/{case_id}")
@private_acl_route
def get_context_trail(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        service = ContextIntelligenceService()
        if case_id.startswith("pr-"):
            return service.load_trail(
                f"context-trail-{case_id}",
                access_context=access_context,
            ).model_dump()
        return service.trace_case(case_id, access_context=access_context).model_dump()
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/context/packs/{case_id}")
@private_acl_route
def get_context_pack(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        service = ContextIntelligenceService()
        if case_id.startswith("pr-"):
            return service.load_context_pack(
                f"context-pack-{case_id}",
                access_context=access_context,
            ).model_dump()
        return service.assemble_case(case_id, access_context=access_context).model_dump()
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/context/prompt-preview/{case_id}")
@private_acl_route
def get_prompt_preview(
    case_id: str,
    access_context: AccessContextDep,
    target: str = "jira_draft",
) -> dict[str, object]:
    try:
        service = ContextIntelligenceService()
        if case_id.startswith("pr-"):
            return service.load_prompt_preview(
                f"prompt-preview-{case_id}-pr_review",
                access_context=access_context,
            ).model_dump()
        return service.prompt_for_case(
            case_id,
            target=target,
            access_context=access_context,
        ).model_dump()
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/context/report")
@private_acl_route
def get_context_report(
    team_id: str,
    access_context: AccessContextDep,
    repo_name: str | None = None,
) -> dict[str, object]:
    try:
        return (
            ContextIntelligenceService()
            .memory_report(
                team_id=team_id,
                repo_name=repo_name,
                access_context=access_context,
            )
            .model_dump()
        )
    except (DreamError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/memory/scan")
def scan_memory(request: MemoryScanRequest) -> dict[str, object]:
    try:
        return (
            MemoryDistillationService()
            .scan(
                team_id=request.team_id,
                repo_path=request.repo_path,
                repo_name=request.repo_name,
            )
            .model_dump()
        )
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
def diff_memory(
    team_id: str,
    scan_id: str = "latest",
    base_scan_id: str | None = None,
) -> dict[str, object]:
    try:
        diff = MemoryDistillationService().diff(
            team_id=team_id,
            scan_id=scan_id,
            base_scan_id=base_scan_id,
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return diff.model_dump()


@router.get("/memory/conflicts")
def get_memory_conflicts(team_id: str, scan_id: str = "latest") -> dict[str, object]:
    try:
        return (
            MemoryDistillationService()
            .conflicts(
                team_id=team_id,
                scan_id=scan_id,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/memory/conflicts/resolve")
def resolve_memory_conflict(request: MemoryConflictResolveRequest) -> dict[str, object]:
    try:
        return (
            MemoryDistillationService()
            .resolve_conflict(
                team_id=request.team_id,
                conflict_id=request.conflict_id,
                winning_claim_id=request.winning_claim_id,
                action=request.action,
                reviewer=request.reviewer,
                reason=request.reason,
                scan_id=request.scan_id,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/memory/conflict-resolutions")
def get_memory_conflict_resolutions(team_id: str) -> dict[str, object]:
    return (
        MemoryDistillationRepository()
        .load_conflict_resolution_ledger(
            team_id,
        )
        .model_dump()
    )


@router.post("/memory/review")
def review_memory_claim(request: MemoryReviewRequest) -> dict[str, object]:
    try:
        return (
            MemoryDistillationService()
            .review_claim(
                team_id=request.team_id,
                claim_id=request.claim_id,
                new_status=request.status,
                reviewer=request.reviewer,
                reason=request.reason,
                scan_id=request.scan_id,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/memory/ledger")
def get_memory_ledger(team_id: str) -> dict[str, object]:
    return MemoryDistillationRepository().load_ledger(team_id).model_dump()


@router.get("/memory/search")
@private_acl_route
def search_memory_claims(
    team_id: str,
    query: str,
    access_context: AccessContextDep,
    scan_id: str = "latest",
    top_k: int = 8,
) -> list[dict[str, object]]:
    try:
        results = MemoryClaimRetriever().search(
            team_id=team_id,
            query=query,
            scan_id=scan_id,
            top_k=top_k,
            access_context=access_context,
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [result.model_dump() for result in results]


@router.get("/memory/context-card")
@private_acl_route
def get_memory_context_card(
    team_id: str,
    query: str,
    access_context: AccessContextDep,
    scan_id: str = "latest",
    top_k: int = 8,
) -> dict[str, object]:
    try:
        markdown = MemoryClaimRetriever().context_card(
            team_id=team_id,
            query=query,
            scan_id=scan_id,
            top_k=top_k,
            access_context=access_context,
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"team_id": team_id, "scan_id": scan_id, "query": query, "markdown": markdown}


@router.post("/memory/eval")
def eval_memory(request: MemoryEvalRequest) -> dict[str, object]:
    try:
        return (
            MemoryDistillationEvaluator()
            .evaluate(
                team_id=request.team_id,
                scan_id=request.scan_id,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/requirement-cases")
@private_acl_route
def create_requirement_case(
    request: RequirementCaseCreateRequest,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .create_case(
                request,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/requirement-cases/{case_id}/analyze")
@private_acl_route
def analyze_requirement_case(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .analyze_case(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases")
@private_acl_route
def list_requirement_cases(
    access_context: AccessContextDep,
) -> list[dict[str, object]]:
    return [
        snapshot.model_dump()
        for snapshot in RequirementCaseService().list_cases(access_context=access_context)
    ]


@router.get("/requirement-cases/{case_id}")
@private_acl_route
def get_requirement_case(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .get_case(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/impact-map")
@private_acl_route
def get_requirement_case_impact(
    case_id: str,
    access_context: AccessContextDep,
) -> list[dict[str, object]]:
    try:
        items = RequirementCaseService().generate_impact_map(
            case_id,
            access_context=access_context,
        )
        return [item.model_dump() for item in items]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/questions")
@private_acl_route
def get_requirement_case_questions(
    case_id: str,
    access_context: AccessContextDep,
    role: str | None = None,
) -> list[dict[str, object]]:
    try:
        questions = RequirementCaseService().generate_questions(
            case_id,
            role=role,
            access_context=access_context,
        )
        return [question.model_dump() for question in questions]
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/requirement-cases/{case_id}/questions/{question_id}/answer")
@private_acl_route
def answer_requirement_case_question(
    case_id: str,
    question_id: str,
    request: RequirementQuestionAnswerRequest,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .answer_question(
                case_id,
                question_id,
                request.answer,
                answered_by=request.answered_by,
                access_context=access_context,
            )
            .model_dump()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/requirement-cases/{case_id}/questions/{question_id}/waive")
@private_acl_route
def waive_requirement_case_question(
    case_id: str,
    question_id: str,
    request: RequirementQuestionWaiveRequest,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .waive_question(
                case_id,
                question_id,
                request.reason,
                waived_by=request.waived_by,
                access_context=access_context,
            )
            .model_dump()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/brief")
@private_acl_route
def get_requirement_case_brief(
    case_id: str,
    access_context: AccessContextDep,
    llm_provider: str = "deterministic",
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService(llm_provider=_optional_llm_provider(llm_provider))
            .generate_engineering_brief(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/jira-draft")
@private_acl_route
def get_requirement_case_jira_draft(
    case_id: str,
    access_context: AccessContextDep,
    llm_provider: str = "deterministic",
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService(llm_provider=_optional_llm_provider(llm_provider))
            .generate_jira_draft(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/jira-draft-context")
@private_acl_route
def get_requirement_case_jira_draft_context(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .prepare_jira_draft_context(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
    except DreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/requirement-cases/{case_id}/jira-readiness")
@private_acl_route
def get_requirement_case_jira_readiness(
    case_id: str,
    access_context: AccessContextDep,
) -> dict[str, object]:
    try:
        return (
            RequirementCaseService()
            .jira_readiness(
                case_id,
                access_context=access_context,
            )
            .model_dump()
        )
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


@router.get("/audit/runs/{run_id}/ratings")
def list_human_ratings(run_id: str) -> list[dict[str, object]]:
    repository = AuditRepository()
    if repository.get_audit_record(run_id) is None:
        raise HTTPException(status_code=404, detail=f"Audit run not found: {run_id}")
    return [rating.model_dump() for rating in repository.list_ratings(run_id)]


@router.post("/audit/runs/{run_id}/ratings")
def rate_audit_run(run_id: str, request: HumanRatingRequest) -> dict[str, object]:
    repository = AuditRepository()
    if repository.get_audit_record(run_id) is None:
        raise HTTPException(status_code=404, detail=f"Audit run not found: {run_id}")
    rating = HumanRatingService(repository=repository).rate(
        run_id=run_id,
        usefulness_score=request.usefulness_score,
        correctness_score=request.correctness_score,
        comments=request.comments,
    )
    return rating.model_dump()


@router.post("/eval/run", response_model=EvaluationResult)
def run_evaluation(request: EvaluationRequest) -> EvaluationResult:
    try:
        return EvaluationAgent(
            llm_judge_provider=_optional_llm_provider(request.judge_provider)
        ).evaluate(request)
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eval/runs/{evaluation_id}/judge", response_model=EvaluationResult)
def judge_evaluation_run(
    evaluation_id: str,
    request: EvaluationJudgeRequest,
) -> EvaluationResult:
    try:
        return EvaluationAgent(
            llm_judge_provider=_optional_llm_provider(request.judge_provider)
        ).judge_existing(evaluation_id)
    except DreamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eval/retrieval", response_model=EvaluationResult)
def run_retrieval_evaluation(request: RetrievalEvalRequest) -> EvaluationResult:
    try:
        return ContextEvaluationService().evaluate_case(
            case_id=request.case_id,
            profile_id=request.profile_id,
        )
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
    payload = scorecard.model_dump()
    markdown_path = scorecard.markdown_path or scorecard.output_path
    if markdown_path:
        try:
            path = resolve_project_path(markdown_path, must_exist=True)
            payload["markdown_report"] = path.read_text(encoding="utf-8")
        except (DreamError, OSError):
            payload["markdown_report"] = ""
    else:
        payload["markdown_report"] = ""
    payload["json_path"] = scorecard.json_path
    payload["markdown_path"] = markdown_path
    payload["warnings"] = scorecard.warnings
    return payload


def _testgen_provider(provider: str) -> MockTestGenProvider | JTestGenAdapter:
    if provider == "mock":
        return MockTestGenProvider()
    if provider == "jtestgen":
        return JTestGenAdapter()
    raise HTTPException(status_code=400, detail=f"Unsupported testgen provider: {provider}")


def _llm_provider(provider: str) -> LLMProvider:
    _enforce_provider_selector(provider)
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    if provider == "qwen-cloud":
        _enforce_public_qwen_rate_limit()
        return QwenCloudProvider()
    if provider in {"config", "plugin"}:
        return _configured_llm_provider()
    raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")


def _optional_llm_provider(
    provider: str,
) -> LLMProvider | None:
    _enforce_provider_selector(provider)
    if provider in {"deterministic", "none"}:
        return None
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    if provider == "qwen-cloud":
        _enforce_public_qwen_rate_limit()
        return QwenCloudProvider()
    if provider in {"config", "plugin"}:
        return _configured_llm_provider()
    raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")


def _enforce_provider_selector(provider: str) -> None:
    try:
        require_private_provider_selector(provider, config=resolve_config())
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _configured_llm_provider() -> LLMProvider:
    provider = build_llm_provider()
    if getattr(provider, "provider_name", "") == "qwen-cloud":
        _enforce_public_qwen_rate_limit()
    return provider


def _enforce_public_qwen_rate_limit() -> None:
    raw_limit = os.getenv("DREAM_PUBLIC_QWEN_REQUESTS_PER_MINUTE", "").strip()
    if not raw_limit:
        return
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Public Qwen rate limit is misconfigured.",
        ) from exc
    if limit <= 0:
        raise HTTPException(
            status_code=503,
            detail="Public Qwen rate limit is misconfigured.",
        )

    now = monotonic()
    cutoff = now - 60.0
    with _PUBLIC_QWEN_RATE_LOCK:
        while _PUBLIC_QWEN_REQUEST_TIMES and _PUBLIC_QWEN_REQUEST_TIMES[0] <= cutoff:
            _PUBLIC_QWEN_REQUEST_TIMES.popleft()
        if len(_PUBLIC_QWEN_REQUEST_TIMES) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Public Qwen demo rate limit reached; retry in one minute.",
            )
        _PUBLIC_QWEN_REQUEST_TIMES.append(now)
