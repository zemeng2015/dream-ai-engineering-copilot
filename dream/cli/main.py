# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Annotated

import typer

from dream import __version__
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.config import resolve_config, sanitized_config_dict, validate_config
from dream.context import ContextEvaluationService, ContextIntelligenceService
from dream.core.errors import DreamError, ProviderConfigurationError
from dream.demo import run_demo_verification
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationRequest
from dream.evals.rating import HumanRatingService
from dream.evals.repository import EvaluationRepository
from dream.extensions import build_llm_provider
from dream.extensions.models import LLMProvider
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRepository, EvidenceGraphRetriever
from dream.intake import KnowledgeIntakeService, ReviewDecision
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.llm import MockLLMProvider, OpenAICompatibleProvider, QwenCloudProvider
from dream.llm.egress import require_private_provider_selector
from dream.memory import (
    MemoryClaimRetriever,
    MemoryDistillationEvaluator,
    MemoryDistillationService,
)
from dream.memory.repository import MemoryDistillationRepository
from dream.pilot_evidence import PilotEvidenceExporter, PilotEvidenceVerifier
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.requirements import RequirementDraftGenerator, RequirementDraftRequest
from dream.review import PRReviewAssistant, PRReviewRequest
from dream.testgen import JTestGenAdapter, MockTestGenProvider, TestGenRequest

app = typer.Typer(help="DREAM AI engineering copilot framework.")
kb_app = typer.Typer(help="Knowledge pack commands.")
requirement_app = typer.Typer(help="Requirement drafting commands.")
review_app = typer.Typer(help="PR review summary commands.")
testgen_app = typer.Typer(help="Test-generation plugin commands.")
audit_app = typer.Typer(help="Audit log commands.")
eval_app = typer.Typer(help="Human evaluation commands.")
codebase_app = typer.Typer(help="Codebase memory commands.")
req_app = typer.Typer(help="Requirement Case intelligence commands.")
llm_app = typer.Typer(help="Optional LLM provider smoke-test commands.")
graph_app = typer.Typer(help="Evidence graph / memory graph commands.")
memory_app = typer.Typer(help="Governed memory distillation commands.")
config_app = typer.Typer(help="Configuration and extension diagnostics.")
demo_app = typer.Typer(help="Deterministic DemoCorp verification commands.")
context_app = typer.Typer(help="Context intelligence and retrieval trust commands.")
intake_app = typer.Typer(help="Knowledge intake and human-review commands.")

app.add_typer(kb_app, name="kb")
app.add_typer(requirement_app, name="requirement")
app.add_typer(review_app, name="review")
app.add_typer(testgen_app, name="testgen")
app.add_typer(audit_app, name="audit")
app.add_typer(eval_app, name="eval")
app.add_typer(codebase_app, name="codebase")
app.add_typer(req_app, name="req")
app.add_typer(llm_app, name="llm")
app.add_typer(graph_app, name="graph")
app.add_typer(memory_app, name="memory")
app.add_typer(config_app, name="config")
app.add_typer(demo_app, name="demo")
app.add_typer(context_app, name="context")
app.add_typer(intake_app, name="intake")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show DREAM version and exit.",
        ),
    ] = False,
) -> None:
    _ = version


@kb_app.command("list-teams")
def list_teams() -> None:
    loader = KnowledgePackLoader()
    for team_id in loader.list_team_ids():
        typer.echo(team_id)


@kb_app.command("search")
def search_kb(
    team: Annotated[str, typer.Option("--team")],
    query: Annotated[str, typer.Option("--query")],
    app_filter: Annotated[str | None, typer.Option("--app")] = None,
    component: Annotated[str | None, typer.Option("--component")] = None,
    doc_type: Annotated[str | None, typer.Option("--doc-type")] = None,
    top_k: Annotated[int, typer.Option("--top-k")] = 5,
) -> None:
    pack_loader = KnowledgePackLoader()
    pack = pack_loader.load(team)
    pack_dir = pack_loader.pack_dir(pack.team_id)
    documents = MarkdownDocumentLoader().load_for_pack(pack, pack_dir)
    chunks = Chunker().chunk_all(documents)
    results = SimpleRetriever(chunks).search(
        query,
        team_id=team,
        app=app_filter,
        component=component,
        doc_type=doc_type,
        top_k=top_k,
    )
    for chunk in results:
        excerpt = " ".join(chunk.content.split())[:220]
        typer.echo(f"Title: {chunk.title}")
        typer.echo(f"Source: {chunk.source_path}")
        typer.echo(f"Excerpt: {excerpt}")
        typer.echo(f"Metadata: {json.dumps(chunk.metadata, sort_keys=True)}")
        typer.echo("")


@requirement_app.command("draft")
def draft_requirement(
    team: Annotated[str, typer.Option("--team")],
    request: Annotated[str, typer.Option("--request")],
    app_filter: Annotated[str | None, typer.Option("--app")] = None,
    component: Annotated[str | None, typer.Option("--component")] = None,
    top_k: Annotated[int, typer.Option("--top-k")] = 5,
    llm_provider: Annotated[str, typer.Option("--llm-provider")] = "mock",
) -> None:
    try:
        response = RequirementDraftGenerator(llm_provider=_llm_provider(llm_provider)).draft(
            RequirementDraftRequest(
                team_id=team,
                rough_business_request=request,
                app=app_filter,
                component=component,
                top_k=top_k,
            )
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(response.markdown)
    typer.echo(f"\nRun ID: {response.run_id}")


@review_app.command("pr")
def review_pr(
    team: Annotated[str, typer.Option("--team")],
    diff: Annotated[str, typer.Option("--diff")],
    jira: Annotated[str | None, typer.Option("--jira")] = None,
    repo: Annotated[str | None, typer.Option("--repo")] = None,
    app_filter: Annotated[str | None, typer.Option("--app")] = None,
    component: Annotated[str | None, typer.Option("--component")] = None,
    top_k: Annotated[int, typer.Option("--top-k")] = 5,
    llm_provider: Annotated[str, typer.Option("--llm-provider")] = "mock",
) -> None:
    try:
        response = PRReviewAssistant(llm_provider=_llm_provider(llm_provider)).review(
            PRReviewRequest(
                team_id=team,
                pr_diff_path=diff,
                jira_context_path=jira,
                repo_name=repo,
                app=app_filter,
                component=component,
                top_k=top_k,
            )
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(response.markdown)
    typer.echo(f"\nRun ID: {response.run_id}")


@testgen_app.command("plan")
def testgen_plan(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    provider: Annotated[str, typer.Option("--provider")] = "mock",
    target_language: Annotated[str, typer.Option("--target-language")] = "java",
) -> None:
    testgen_provider = _testgen_provider(provider)
    plan = testgen_provider.plan(
        TestGenRequest(team_id=team, repo_path=repo, target_language=target_language)
    )
    typer.echo(plan.model_dump_json(indent=2))


@testgen_app.command("run")
def testgen_run(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    provider: Annotated[str, typer.Option("--provider")] = "mock",
    target_language: Annotated[str, typer.Option("--target-language")] = "java",
    dry_run: Annotated[bool, typer.Option("--dry-run/--no-dry-run")] = True,
) -> None:
    testgen_provider = _testgen_provider(provider)
    result = testgen_provider.run(
        TestGenRequest(
            team_id=team,
            repo_path=repo,
            target_language=target_language,
            dry_run=dry_run,
        )
    )
    typer.echo(result.report_markdown)
    typer.echo(f"\nRun ID: {result.run_id}")


@codebase_app.command("index")
def codebase_index(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    name: Annotated[str | None, typer.Option("--name")] = None,
) -> None:
    index = CodebaseIndexer().index(team_id=team, repo_path=repo, repo_name=name)
    index_path = CodebaseIndexRepository().display_index_path(team, index.repo_name)
    typer.echo(f"Repo: {index.repo_name}")
    typer.echo(f"Files: {len(index.files)}")
    typer.echo(f"Symbols: {len(index.symbols)}")
    typer.echo(f"Tests: {len(index.tests)}")
    typer.echo(f"Concepts: {len(index.concepts)}")
    typer.echo(f"Index: {index_path}")


@codebase_app.command("search")
def codebase_search(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    query: Annotated[str, typer.Option("--query")],
    top_k: Annotated[int, typer.Option("--top-k")] = 5,
) -> None:
    results = CodebaseRetriever().search(team_id=team, repo_name=repo, query=query, top_k=top_k)
    for result in results:
        typer.echo(f"Type: {result.result_type}")
        typer.echo(f"Title: {result.title}")
        typer.echo(f"Source: {result.source_path}")
        typer.echo(f"Excerpt: {result.excerpt}")
        typer.echo(f"Reason: {result.reason}")
        typer.echo("")


@codebase_app.command("concepts")
def codebase_concepts(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
) -> None:
    index = CodebaseIndexRepository().load(team, repo)
    for concept in index.concepts:
        typer.echo(f"{concept.concept}\tfiles={len(concept.related_files)}")


@codebase_app.command("show")
def codebase_show(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    file: Annotated[str, typer.Option("--file")],
) -> None:
    file_node = CodebaseRetriever().find_file(team_id=team, repo_name=repo, file_path=file)
    if file_node is None:
        raise typer.BadParameter(f"File not found in codebase index: {file}")
    typer.echo(file_node.model_dump_json(indent=2))


@graph_app.command("build")
def graph_build(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
) -> None:
    graph = EvidenceGraphBuilder().build(team_id=team, repo_name=repo)
    graph_path = EvidenceGraphRepository().display_graph_path(team, repo)
    typer.echo(f"team_id: {graph.team_id}")
    typer.echo(f"repo_name: {graph.repo_name or '_team'}")
    typer.echo(f"nodes: {len(graph.nodes)}")
    typer.echo(f"edges: {len(graph.edges)}")
    typer.echo(f"graph: {graph_path}")
    if graph.warnings:
        typer.echo("warnings:")
        for warning in graph.warnings:
            typer.echo(f"- {warning}")


@graph_app.command("search")
def graph_search(
    team: Annotated[str, typer.Option("--team")],
    query: Annotated[str, typer.Option("--query")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
    top_k: Annotated[int, typer.Option("--top-k")] = 8,
) -> None:
    results = EvidenceGraphRetriever().search(
        team_id=team,
        repo_name=repo,
        query=query,
        top_k=top_k,
    )
    for result in results:
        typer.echo(f"Type: {result.node.node_type}")
        typer.echo(f"Title: {result.node.title}")
        typer.echo(f"Source: {result.node.source_path or result.node.key}")
        typer.echo(f"Score: {result.score}")
        typer.echo("Evidence paths:")
        for path in result.evidence_paths[:6]:
            typer.echo(f"- {path}")
        typer.echo("")


@graph_app.command("explain")
def graph_explain(
    team: Annotated[str, typer.Option("--team")],
    concept: Annotated[str, typer.Option("--concept")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
) -> None:
    result = EvidenceGraphRetriever().explain(team_id=team, repo_name=repo, query=concept)
    typer.echo(f"query: {result.query}")
    typer.echo(f"nodes: {len(result.matched_nodes)}")
    for node in result.matched_nodes:
        typer.echo(f"- [{node.node_type}] {node.title} ({node.source_path or node.key})")
    typer.echo("evidence_paths:")
    for path in result.evidence_paths:
        typer.echo(f"- {path}")


@graph_app.command("neighbors")
def graph_neighbors(
    team: Annotated[str, typer.Option("--team")],
    node: Annotated[str, typer.Option("--node")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
) -> None:
    result = EvidenceGraphRetriever().neighbors(team_id=team, repo_name=repo, node=node)
    typer.echo(f"query: {result.query}")
    for matched_node in result.matched_nodes:
        typer.echo(
            f"- [{matched_node.node_type}] {matched_node.title} "
            f"({matched_node.source_path or matched_node.key})"
        )
    typer.echo("evidence_paths:")
    for path in result.evidence_paths:
        typer.echo(f"- {path}")


@memory_app.command("scan")
def memory_scan(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str, typer.Option("--repo")],
    name: Annotated[str | None, typer.Option("--name")] = None,
) -> None:
    try:
        scan = MemoryDistillationService().scan(
            team_id=team,
            repo_path=repo,
            repo_name=name,
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    repository = MemoryDistillationRepository()
    typer.echo(f"scan_id: {scan.scan_id}")
    typer.echo(f"team_id: {scan.team_id}")
    typer.echo(f"repo_name: {scan.repo_name or '_team'}")
    typer.echo(f"schema_version: {scan.schema_version}")
    typer.echo(f"commit_sha: {scan.provenance.commit_sha if scan.provenance else 'unknown'}")
    typer.echo(f"dirty: {scan.provenance.dirty if scan.provenance else 'unknown'}")
    typer.echo(f"sources: {len(scan.sources)}")
    typer.echo(f"claims: {len(scan.claims)}")
    typer.echo(f"structural_claims: {scan.validation.structural_claims}")
    typer.echo(f"semantic_candidate_claims: {scan.validation.semantic_candidate_claims}")
    typer.echo(f"citation_validity: {scan.validation.citation_validity:.2f}")
    typer.echo(f"scan: {repository.display_scan_path(scan.team_id, scan.scan_id)}")
    typer.echo(f"latest: {repository.display_latest_scan_path(scan.team_id)}")


@memory_app.command("diff")
def memory_diff(
    team: Annotated[str, typer.Option("--team")],
    scan: Annotated[str, typer.Option("--scan")] = "latest",
    base: Annotated[str | None, typer.Option("--base")] = None,
) -> None:
    try:
        typer.echo(
            MemoryDistillationService().diff_markdown(
                team_id=team,
                scan_id=scan,
                base_scan_id=base,
            )
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc


@memory_app.command("review")
def memory_review(
    team: Annotated[str, typer.Option("--team")],
    claim: Annotated[str, typer.Option("--claim")],
    status: Annotated[str, typer.Option("--status")],
    reviewer: Annotated[str | None, typer.Option("--reviewer")] = None,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    scan: Annotated[str, typer.Option("--scan")] = "latest",
) -> None:
    try:
        event = MemoryDistillationService().review_claim(
            team_id=team,
            claim_id=claim,
            new_status=status,
            reviewer=reviewer,
            reason=reason,
            scan_id=scan,
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    repository = MemoryDistillationRepository()
    typer.echo(event.model_dump_json(indent=2))
    typer.echo(f"ledger: {repository.display_ledger_path(event.team_id)}")


@memory_app.command("ledger")
def memory_ledger(team: Annotated[str, typer.Option("--team")]) -> None:
    typer.echo(MemoryDistillationRepository().load_ledger(team).model_dump_json(indent=2))


@memory_app.command("search")
def memory_search(
    team: Annotated[str, typer.Option("--team")],
    query: Annotated[str, typer.Option("--query")],
    scan: Annotated[str, typer.Option("--scan")] = "latest",
    top_k: Annotated[int, typer.Option("--top-k")] = 8,
) -> None:
    try:
        results = MemoryClaimRetriever().search(
            team_id=team,
            query=query,
            scan_id=scan,
            top_k=top_k,
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps([result.model_dump() for result in results], indent=2))


@memory_app.command("context")
def memory_context(
    team: Annotated[str, typer.Option("--team")],
    query: Annotated[str, typer.Option("--query")],
    scan: Annotated[str, typer.Option("--scan")] = "latest",
    top_k: Annotated[int, typer.Option("--top-k")] = 8,
) -> None:
    try:
        typer.echo(
            MemoryClaimRetriever().context_card(
                team_id=team,
                query=query,
                scan_id=scan,
                top_k=top_k,
            )
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc


@memory_app.command("eval")
def memory_eval(
    team: Annotated[str, typer.Option("--team")],
    scan: Annotated[str, typer.Option("--scan")] = "latest",
) -> None:
    try:
        result = MemoryDistillationEvaluator().evaluate(team_id=team, scan_id=scan)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    repository = MemoryDistillationRepository()
    typer.echo(result.markdown_report)
    typer.echo(f"JSON: {repository.display_eval_path(result.team_id, result.evaluation_id)}")


@req_app.command("create")
def req_create(
    team: Annotated[str, typer.Option("--team")],
    request: Annotated[str, typer.Option("--request")],
    role: Annotated[str | None, typer.Option("--role")] = None,
    app_filter: Annotated[str | None, typer.Option("--app")] = None,
    component: Annotated[str | None, typer.Option("--component")] = None,
) -> None:
    snapshot = RequirementCaseService().create_case(
        RequirementCaseCreateRequest(
            team_id=team,
            raw_request=request,
            created_by_role=role,
            target_app=app_filter,
            target_component=component,
        )
    )
    typer.echo(f"case_id: {snapshot.case.case_id}")
    typer.echo(f"title: {snapshot.case.title}")
    typer.echo(f"status: {snapshot.case.status}")


@req_app.command("analyze")
def req_analyze(case: Annotated[str, typer.Option("--case")]) -> None:
    snapshot = RequirementCaseService().analyze_case(case)
    typer.echo(f"case_id: {snapshot.case.case_id}")
    typer.echo(f"evidence_items: {len(snapshot.evidence)}")
    typer.echo(f"impact_items: {len(snapshot.impact_items)}")
    typer.echo(f"questions: {len(snapshot.questions)}")


@req_app.command("impact")
def req_impact(case: Annotated[str, typer.Option("--case")]) -> None:
    items = RequirementCaseService().generate_impact_map(case)
    for item in items:
        typer.echo(f"{item.area_type}\t{item.name}\tconfidence={item.confidence:.2f}")
        typer.echo(f"  {item.description}")
        typer.echo(f"  sources: {', '.join(item.sources) or 'inferred'}")


@req_app.command("questions")
def req_questions(
    case: Annotated[str, typer.Option("--case")],
    role: Annotated[str | None, typer.Option("--role")] = None,
) -> None:
    questions = RequirementCaseService().generate_questions(case, role=role)
    for question in questions:
        typer.echo(f"{question.question_id}\t[{question.target_role}]\t{question.status}")
        typer.echo(question.question)
        if question.answer:
            typer.echo(f"Answer: {question.answer}")
        typer.echo(f"Why: {question.why_it_matters}")
        typer.echo("")


@req_app.command("answer")
def req_answer(
    case: Annotated[str, typer.Option("--case")],
    question: Annotated[str, typer.Option("--question")],
    answer: Annotated[str, typer.Option("--answer")],
    answered_by: Annotated[str | None, typer.Option("--answered-by")] = None,
) -> None:
    try:
        updated = RequirementCaseService().answer_question(
            case,
            question,
            answer,
            answered_by=answered_by,
        )
    except (DreamError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(updated.model_dump_json(indent=2))


@req_app.command("readiness")
def req_readiness(case: Annotated[str, typer.Option("--case")]) -> None:
    try:
        readiness = RequirementCaseService().jira_readiness(case)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(readiness.model_dump_json(indent=2))


@req_app.command("brief")
def req_brief(
    case: Annotated[str, typer.Option("--case")],
    llm_provider: Annotated[str, typer.Option("--llm-provider")] = "deterministic",
) -> None:
    try:
        brief = RequirementCaseService(
            llm_provider=_optional_llm_provider(llm_provider)
        ).generate_engineering_brief(case)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(brief.markdown)


@req_app.command("jira")
def req_jira(
    case: Annotated[str, typer.Option("--case")],
    llm_provider: Annotated[str, typer.Option("--llm-provider")] = "deterministic",
) -> None:
    try:
        jira = RequirementCaseService(
            llm_provider=_optional_llm_provider(llm_provider)
        ).generate_jira_draft(case)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(jira.markdown)


@req_app.command("show")
def req_show(case: Annotated[str, typer.Option("--case")]) -> None:
    snapshot = RequirementCaseService().get_case(case)
    typer.echo(snapshot.model_dump_json(indent=2))


@req_app.command("list")
def req_list() -> None:
    for snapshot in RequirementCaseService().list_cases():
        typer.echo(
            f"{snapshot.case.case_id}\t{snapshot.case.status}\t"
            f"{snapshot.case.team_id}\t{snapshot.case.title}"
        )


@audit_app.command("list")
def audit_list() -> None:
    records = AuditRepository().list_audit_records()
    for record in records:
        typer.echo(
            f"{record.run_id}\t{record.use_case}\t{record.team_id}\t"
            f"{record.status}\t{record.output_path}"
        )


@audit_app.command("show")
def audit_show(run_id: str) -> None:
    record = AuditRepository().get_audit_record(run_id)
    if record is None:
        raise typer.BadParameter(f"Audit run not found: {run_id}")
    typer.echo(record.model_dump_json(indent=2))


@audit_app.command("export-bundle")
def audit_export_bundle(
    team: Annotated[str, typer.Option("--team")],
    confirm_team: Annotated[str, typer.Option("--confirm-team")],
    operator: Annotated[str, typer.Option("--operator")],
    reason: Annotated[str, typer.Option("--reason")],
    output_root: Annotated[Path | None, typer.Option("--output-root")] = None,
) -> None:
    try:
        result = PilotEvidenceExporter().build(
            team_id=team,
            confirm_team=confirm_team,
            operator_id=operator,
            reason=reason,
            output_root=output_root,
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(result.model_dump_json(indent=2))


@audit_app.command("verify-bundle")
def audit_verify_bundle(
    bundle: Annotated[Path, typer.Option("--bundle")],
    expected_root_sha256: Annotated[
        str | None,
        typer.Option("--expected-root-sha256"),
    ] = None,
) -> None:
    report = PilotEvidenceVerifier().verify(
        bundle,
        expected_root_sha256=expected_root_sha256,
    )
    typer.echo(report.model_dump_json(indent=2))
    if not report.passed:
        raise typer.Exit(code=1)


@eval_app.command("rate")
def eval_rate(
    run_id: str,
    usefulness: Annotated[int, typer.Option("--usefulness", min=1, max=5)],
    correctness: Annotated[int, typer.Option("--correctness", min=1, max=5)],
    comments: Annotated[str, typer.Option("--comments")],
) -> None:
    rating = HumanRatingService().rate(
        run_id=run_id,
        usefulness_score=usefulness,
        correctness_score=correctness,
        comments=comments,
    )
    typer.echo(rating.model_dump_json(indent=2))


@eval_app.command("run")
def eval_run(
    target_type: Annotated[str, typer.Option("--target-type")],
    artifact: Annotated[str | None, typer.Option("--artifact")] = None,
    case: Annotated[str | None, typer.Option("--case")] = None,
    run: Annotated[str | None, typer.Option("--run")] = None,
    team: Annotated[str | None, typer.Option("--team")] = None,
    repo: Annotated[str | None, typer.Option("--repo")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    strict: Annotated[bool, typer.Option("--strict/--no-strict")] = False,
) -> None:
    try:
        result = EvaluationAgent().evaluate(
            EvaluationRequest(
                target_type=target_type,
                artifact_path=artifact,
                case_id=case,
                run_id=run,
                team_id=team,
                repo_name=repo,
                expected_profile=profile,
                strict=strict,
            )
        )
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(result.markdown_report)
    typer.echo(f"JSON: {result.json_path}")
    typer.echo(f"Markdown: {result.markdown_path}")


@eval_app.command("retrieval")
def eval_retrieval(
    case: Annotated[str, typer.Option("--case")],
    profile: Annotated[str, typer.Option("--profile")],
) -> None:
    try:
        result = ContextEvaluationService().evaluate_case(case_id=case, profile_id=profile)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(result.markdown_report)
    typer.echo(f"JSON: {result.json_path}")
    typer.echo(f"Markdown: {result.markdown_path}")


@eval_app.command("list")
def eval_list() -> None:
    for scorecard in EvaluationRepository().list():
        typer.echo(
            f"{scorecard.evaluation_id}\t{scorecard.target_type}\t"
            f"{scorecard.overall_score:.2f}\t{scorecard.grade}\t{scorecard.pass_status}"
        )


@eval_app.command("show")
def eval_show(evaluation_id: str) -> None:
    scorecard = EvaluationRepository().get(evaluation_id)
    if scorecard is None:
        raise typer.BadParameter(f"Evaluation not found: {evaluation_id}")
    typer.echo(scorecard.model_dump_json(indent=2))


@llm_app.command("smoke")
def llm_smoke(
    provider: Annotated[str, typer.Option("--provider")] = "mock",
    prompt: Annotated[
        str,
        typer.Option("--prompt"),
    ] = "Reply with DREAM_OK and one short phrase.",
) -> None:
    llm_provider = _llm_provider(provider)

    try:
        response = llm_provider.complete(prompt)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"provider: {response.provider_name}")
    typer.echo(f"model: {response.model_name}")
    typer.echo("text:")
    typer.echo(response.text)


@context_app.command("trace")
def context_trace(case: Annotated[str, typer.Option("--case")]) -> None:
    trail = ContextIntelligenceService().trace_case(case)
    typer.echo(trail.model_dump_json(indent=2))
    typer.echo(f"JSON: {trail.json_path}")
    typer.echo(f"Markdown: {trail.markdown_path}")


@context_app.command("assemble")
def context_assemble(case: Annotated[str, typer.Option("--case")]) -> None:
    pack = ContextIntelligenceService().assemble_case(case)
    typer.echo(pack.model_dump_json(indent=2))
    typer.echo(f"JSON: {pack.json_path}")
    typer.echo(f"Markdown: {pack.markdown_path}")


@context_app.command("prompt")
def context_prompt(
    case: Annotated[str, typer.Option("--case")],
    target: Annotated[str, typer.Option("--target")] = "jira_draft",
) -> None:
    preview = ContextIntelligenceService().prompt_for_case(case, target=target)
    typer.echo(preview.prompt_text)
    typer.echo(f"\nJSON: {preview.json_path}")
    typer.echo(f"Markdown: {preview.markdown_path}")


@context_app.command("card")
def context_card(
    team: Annotated[str, typer.Option("--team")],
    source: Annotated[str, typer.Option("--source")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
) -> None:
    card = ContextIntelligenceService().evidence_card(
        team_id=team,
        repo_name=repo,
        source_path=source,
    )
    typer.echo(card.model_dump_json(indent=2))


@context_app.command("report")
def context_report(
    team: Annotated[str, typer.Option("--team")],
    repo: Annotated[str | None, typer.Option("--repo")] = None,
) -> None:
    report = ContextIntelligenceService().memory_report(team_id=team, repo_name=repo)
    typer.echo(report.model_dump_json(indent=2))
    typer.echo(f"JSON: {report.json_path}")
    typer.echo(f"Markdown: {report.markdown_path}")


@intake_app.command("upload")
def intake_upload(
    team: Annotated[str, typer.Option("--team")],
    file: Annotated[str, typer.Option("--file")],
    doc_type: Annotated[str, typer.Option("--type")] = "architecture",
    title: Annotated[str | None, typer.Option("--title")] = None,
) -> None:
    document = KnowledgeIntakeService().upload_local_file(
        team_id=team,
        file_path=file,
        document_type=doc_type,
        title=title,
    )
    typer.echo(document.model_dump_json(indent=2))


@intake_app.command("list")
def intake_list() -> None:
    for document in KnowledgeIntakeService().repository.list_documents():
        typer.echo(
            f"{document.document_id}\t{document.team_id}\t{document.document_type}\t"
            f"{document.status}\t{document.title}"
        )


@intake_app.command("parse")
def intake_parse(document: Annotated[str, typer.Option("--document")]) -> None:
    draft = KnowledgeIntakeService().parse_document(document)
    typer.echo(draft.model_dump_json(indent=2))
    typer.echo(f"JSON: {draft.json_path}")
    typer.echo(f"Markdown: {draft.markdown_path}")


@intake_app.command("review")
def intake_review(
    draft: Annotated[str, typer.Option("--draft")],
    status: Annotated[str, typer.Option("--status")],
    reviewer: Annotated[str | None, typer.Option("--reviewer")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    updated = KnowledgeIntakeService().review_draft(
        draft,
        ReviewDecision(status=status, reviewer=reviewer, notes=notes),
    )
    typer.echo(updated.model_dump_json(indent=2))


@intake_app.command("promote")
def intake_promote(draft: Annotated[str, typer.Option("--draft")]) -> None:
    result = KnowledgeIntakeService().promote_draft(draft)
    typer.echo(result.model_dump_json(indent=2))


@config_app.command("show")
def config_show() -> None:
    resolved = resolve_config()
    typer.echo(json.dumps(sanitized_config_dict(resolved), indent=2, sort_keys=True))


@config_app.command("validate")
def config_validate() -> None:
    report = validate_config()
    if report.ok:
        typer.echo("DREAM config validate: PASS")
    else:
        typer.echo("DREAM config validate: FAIL")
    _echo_config_diagnostics(report.diagnostics)
    if not report.ok:
        raise typer.Exit(code=1)


@config_app.command("doctor")
def config_doctor() -> None:
    report = validate_config(create_artifact_root=False)
    config = report.config
    typer.echo("DREAM Config Doctor")
    typer.echo(f"mode: {config.mode}")
    typer.echo(f"llm_provider: {config.llm.provider}")
    typer.echo(f"knowledge_root: {config.knowledge.root}")
    typer.echo(f"artifact_root: {config.artifacts.root}")
    typer.echo(f"audit_sqlite_path: {config.audit.sqlite_path}")
    if not report.diagnostics:
        typer.echo("diagnostics: none")
    else:
        typer.echo("diagnostics:")
        _echo_config_diagnostics(report.diagnostics)
    if not report.ok:
        raise typer.Exit(code=1)


@demo_app.command("verify")
def demo_verify() -> None:
    result = run_demo_verification()
    if result.passed:
        typer.echo("DREAM Demo Verification: PASS")
        return
    failure = result.failure
    typer.echo("DREAM Demo Verification: FAIL")
    if failure is not None:
        typer.echo(f"step: {failure.step}")
        typer.echo(f"error: {failure.error}")
        typer.echo(f"recommended_fix: {failure.recommended_fix}")
    raise typer.Exit(code=1)


def _testgen_provider(provider: str) -> MockTestGenProvider | JTestGenAdapter:
    if provider == "mock":
        return MockTestGenProvider()
    if provider == "jtestgen":
        return JTestGenAdapter()
    raise typer.BadParameter(f"Unsupported testgen provider: {provider}")


def _llm_provider(provider: str) -> LLMProvider:
    try:
        require_private_provider_selector(provider, config=resolve_config())
    except ProviderConfigurationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    if provider == "qwen-cloud":
        return QwenCloudProvider()
    if provider in {"config", "plugin"}:
        return build_llm_provider()
    raise typer.BadParameter(f"Unsupported LLM provider: {provider}")


def _optional_llm_provider(provider: str) -> LLMProvider | None:
    if provider == "deterministic":
        return None
    return _llm_provider(provider)


def _echo_config_diagnostics(diagnostics) -> None:
    for item in diagnostics:
        typer.echo(f"{item.severity}: {item.message}")
        if item.recommended_fix:
            typer.echo(f"  fix: {item.recommended_fix}")


if __name__ == "__main__":
    app()
