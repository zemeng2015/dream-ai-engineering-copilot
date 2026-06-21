# SPDX-License-Identifier: Apache-2.0

import json
from typing import Annotated

import typer

from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.core.errors import DreamError
from dream.core.paths import KNOWLEDGE_PACKS_DIR
from dream.evals.evaluator import EvaluationAgent
from dream.evals.models import EvaluationRequest
from dream.evals.rating import HumanRatingService
from dream.evals.repository import EvaluationRepository
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.llm import MockLLMProvider, OpenAICompatibleProvider
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

app.add_typer(kb_app, name="kb")
app.add_typer(requirement_app, name="requirement")
app.add_typer(review_app, name="review")
app.add_typer(testgen_app, name="testgen")
app.add_typer(audit_app, name="audit")
app.add_typer(eval_app, name="eval")
app.add_typer(codebase_app, name="codebase")
app.add_typer(req_app, name="req")
app.add_typer(llm_app, name="llm")


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
    pack_dir = KNOWLEDGE_PACKS_DIR / pack.team_id
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
        typer.echo(f"[{question.target_role}] {question.question}")
        typer.echo(f"Why: {question.why_it_matters}")
        typer.echo("")


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
    if provider == "mock":
        llm_provider = MockLLMProvider()
    elif provider == "openai-compatible":
        llm_provider = OpenAICompatibleProvider()
    else:
        raise typer.BadParameter(f"Unsupported LLM provider: {provider}")

    try:
        response = llm_provider.complete(prompt)
    except DreamError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"provider: {response.provider_name}")
    typer.echo(f"model: {response.model_name}")
    typer.echo("text:")
    typer.echo(response.text)


def _testgen_provider(provider: str) -> MockTestGenProvider | JTestGenAdapter:
    if provider == "mock":
        return MockTestGenProvider()
    if provider == "jtestgen":
        return JTestGenAdapter()
    raise typer.BadParameter(f"Unsupported testgen provider: {provider}")


def _llm_provider(provider: str) -> MockLLMProvider | OpenAICompatibleProvider:
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider()
    raise typer.BadParameter(f"Unsupported LLM provider: {provider}")


def _optional_llm_provider(provider: str) -> MockLLMProvider | OpenAICompatibleProvider | None:
    if provider == "deterministic":
        return None
    return _llm_provider(provider)


if __name__ == "__main__":
    app()
