# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from pathlib import Path

from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer
from dream.core.paths import PROJECT_ROOT
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationRequest
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.review import PRReviewAssistant, PRReviewRequest


@dataclass(frozen=True)
class DemoVerificationFailure:
    step: str
    error: str
    recommended_fix: str


@dataclass(frozen=True)
class DemoVerificationResult:
    passed: bool
    failure: DemoVerificationFailure | None = None


def run_demo_verification() -> DemoVerificationResult:
    steps = [
        ("knowledge pack loads", _verify_knowledge_pack),
        ("kb search works", _verify_kb_search),
        ("codebase index works", _verify_codebase_index),
        ("requirement case create/analyze works", _verify_requirement_case),
        ("brief and Jira draft generation works", _verify_brief_and_jira),
        ("PR review works on fake diff", _verify_pr_review),
        ("eval run works on example output", _verify_eval),
        ("audit list works", _verify_audit_list),
    ]
    state: dict[str, object] = {}
    for step_name, step in steps:
        try:
            step(state)
        except Exception as exc:  # noqa: BLE001 - CLI needs concise diagnostics.
            return DemoVerificationResult(
                passed=False,
                failure=DemoVerificationFailure(
                    step=step_name,
                    error=str(exc),
                    recommended_fix=_recommended_fix(step_name),
                ),
            )
    return DemoVerificationResult(passed=True)


def _verify_knowledge_pack(state: dict[str, object]) -> None:
    loader = KnowledgePackLoader()
    pack = loader.load("demo_team")
    state["pack_loader"] = loader
    state["pack"] = pack


def _verify_kb_search(state: dict[str, object]) -> None:
    loader = _state(state, "pack_loader", KnowledgePackLoader)
    pack = _state(state, "pack", object)
    pack_dir = loader.pack_dir(pack.team_id)
    documents = MarkdownDocumentLoader().load_for_pack(pack, pack_dir)
    chunks = Chunker().chunk_all(documents)
    results = SimpleRetriever(chunks).search(
        "async status tracking",
        team_id="demo_team",
        top_k=3,
    )
    if not results:
        raise RuntimeError("No knowledge chunks returned for demo query.")


def _verify_codebase_index(state: dict[str, object]) -> None:
    repo_path = _demo_repo_path()
    index = CodebaseIndexer().index(
        team_id="demo_team",
        repo_path=repo_path,
        repo_name=repo_path.name,
    )
    if not index.files:
        raise RuntimeError(f"No files indexed from {repo_path}")
    state["repo_name"] = index.repo_name


def _verify_requirement_case(state: dict[str, object]) -> None:
    service = RequirementCaseService()
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request="Add async status tracking for long-running job execution.",
            created_by_role="BA",
        )
    )
    analyzed = service.analyze_case(snapshot.case.case_id)
    if not analyzed.impact_items:
        raise RuntimeError("Requirement case analysis produced no impact items.")
    state["requirement_service"] = service
    state["case_id"] = analyzed.case.case_id


def _verify_brief_and_jira(state: dict[str, object]) -> None:
    service = _state(state, "requirement_service", RequirementCaseService)
    case_id = _state(state, "case_id", str)
    brief = service.generate_engineering_brief(case_id)
    jira = service.generate_jira_draft(case_id)
    if "# Engineering Brief" not in brief.markdown:
        raise RuntimeError("Engineering brief did not include expected heading.")
    if "# Jira Story Draft" not in jira.markdown:
        raise RuntimeError("Jira draft did not include expected heading.")


def _verify_pr_review(state: dict[str, object]) -> None:
    response = PRReviewAssistant().review(
        PRReviewRequest(
            team_id="demo_team",
            pr_diff_path="examples/fake_pr_diff.diff",
            jira_context_path="examples/fake_jira_ticket.md",
            repo_name=None,
        )
    )
    if not response.markdown.strip():
        raise RuntimeError("PR review returned empty markdown.")


def _verify_eval(state: dict[str, object]) -> None:
    result = EvaluationAgent().evaluate(
        EvaluationRequest(
            target_type="pr_review",
            artifact_path="examples/outputs/pr-review-output-collector-example.md",
            team_id="demo_team",
            repo_name=str(state.get("repo_name") or ""),
        )
    )
    if not result.scorecard.pass_status:
        raise RuntimeError("Evaluation did not produce a pass status.")


def _verify_audit_list(state: dict[str, object]) -> None:
    records = AuditRepository().list_audit_records()
    if not records:
        raise RuntimeError("Audit list returned no records after demo verification steps.")


def _demo_repo_path() -> Path:
    dfp_repo = PROJECT_ROOT / "examples" / "dfp-demo-repo"
    if dfp_repo.exists():
        return dfp_repo
    return PROJECT_ROOT / "examples" / "java-demo-repo"


def _recommended_fix(step_name: str) -> str:
    fixes = {
        "knowledge pack loads": (
            "Check knowledge_packs/demo_team/team.yaml and config knowledge root."
        ),
        "kb search works": "Check demo knowledge documents and chunking inputs.",
        "codebase index works": "Check examples/dfp-demo-repo or examples/java-demo-repo exists.",
        "requirement case create/analyze works": "Check SQLite audit path and demo knowledge pack.",
        "brief and Jira draft generation works": (
            "Check requirement case persistence and deterministic generators."
        ),
        "PR review works on fake diff": (
            "Check examples/fake_pr_diff.diff and examples/fake_jira_ticket.md."
        ),
        "eval run works on example output": (
            "Check examples/outputs/pr-review-output-collector-example.md."
        ),
        "audit list works": "Check audit SQLite path is writable.",
    }
    return fixes.get(step_name, "Run pytest for a fuller failure trace.")


def _state(state: dict[str, object], key: str, expected_type: type):
    value = state.get(key)
    if not isinstance(value, expected_type):
        raise RuntimeError(f"Demo verifier state missing {key}.")
    return value
