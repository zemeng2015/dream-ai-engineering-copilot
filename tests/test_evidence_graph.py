# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository, CodebaseRetriever
from dream.graph import EvidenceGraphBuilder, EvidenceGraphRepository, EvidenceGraphRetriever
from dream.memory import EngineeringMemoryRetriever
from dream.requirement_cases import (
    RequirementCaseCreateRequest,
    RequirementCaseRepository,
    RequirementCaseService,
)
from dream.review import PRReviewAssistant, PRReviewRequest


def _build_dfp_graph(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    codebase_repository = CodebaseIndexRepository(artifacts_dir)
    CodebaseIndexer(repository=codebase_repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/dfp-demo-repo",
        repo_name="dfp-demo-repo",
    )
    graph_repository = EvidenceGraphRepository(artifacts_dir)
    graph = EvidenceGraphBuilder(
        codebase_repository=codebase_repository,
        repository=graph_repository,
        audit_logger=audit_logger,
    ).build(team_id="demo_team", repo_name="dfp-demo-repo")
    return graph, graph_repository, codebase_repository, audit_logger


def test_evidence_graph_builder_writes_nodes_edges_and_json(tmp_path) -> None:
    graph, graph_repository, _, _ = _build_dfp_graph(tmp_path)

    graph_path = graph_repository.graph_path("demo_team", "dfp-demo-repo")
    node_titles = {node.title for node in graph.nodes}
    edge_types = {edge.edge_type for edge in graph.edges}

    assert graph_path.exists()
    assert "execution status" in {node.key for node in graph.nodes if node.node_type == "concept"}
    assert "backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java" in node_titles
    assert "Status stuck RUNNING" in node_titles
    assert {"IMPLEMENTED_BY", "TESTED_BY", "REGRESSED_BY"}.issubset(edge_types)


def test_evidence_graph_retriever_explains_execution_status(tmp_path) -> None:
    _, graph_repository, _, _ = _build_dfp_graph(tmp_path)
    retriever = EvidenceGraphRetriever(repository=graph_repository)

    results = retriever.search(
        team_id="demo_team",
        repo_name="dfp-demo-repo",
        query="execution status",
        top_k=10,
    )
    explanation = retriever.explain(
        team_id="demo_team",
        repo_name="dfp-demo-repo",
        query="execution status",
    )
    text = "\n".join(
        [
            *(result.node.title for result in results),
            *(path for result in results for path in result.evidence_paths),
            *explanation.evidence_paths,
        ]
    )

    assert "StatusTracker.java" in text
    assert "INC-103" in text or "Status stuck RUNNING" in text
    assert "DFP-101" in text or "Add execution status tracking" in text


def test_requirement_case_uses_graph_evidence_when_graph_exists(tmp_path) -> None:
    _, graph_repository, codebase_repository, audit_logger = _build_dfp_graph(tmp_path)
    memory_retriever = EngineeringMemoryRetriever(
        codebase_repository=codebase_repository,
        codebase_retriever=CodebaseRetriever(repository=codebase_repository),
        graph_repository=graph_repository,
        graph_retriever=EvidenceGraphRetriever(repository=graph_repository),
    )
    service = RequirementCaseService(
        repository=RequirementCaseRepository(tmp_path / "cases.sqlite"),
        memory_retriever=memory_retriever,
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
    )
    snapshot = service.create_case(
        RequirementCaseCreateRequest(
            team_id="demo_team",
            raw_request=(
                "Users want to know which task is still running when a forecast "
                "job takes too long"
            ),
            created_by_role="BA",
        )
    )

    analyzed = service.analyze_case(snapshot.case.case_id)

    assert any(item.source_type.startswith("graph_") for item in analyzed.evidence)
    assert any(
        "StatusTracker" in item.excerpt or "INC-103" in item.excerpt
        for item in analyzed.evidence
    )


def test_pr_review_uses_evidence_graph_for_changed_files(tmp_path) -> None:
    _, graph_repository, codebase_repository, audit_logger = _build_dfp_graph(tmp_path)
    assistant = PRReviewAssistant(
        audit_logger=audit_logger,
        codebase_repository=codebase_repository,
        codebase_retriever=CodebaseRetriever(repository=codebase_repository),
        graph_repository=graph_repository,
        graph_retriever=EvidenceGraphRetriever(repository=graph_repository),
    )

    response = assistant.review(
        PRReviewRequest(
            team_id="demo_team",
            repo_name="dfp-demo-repo",
            pr_diff_path="examples/pr-diffs/DFP-110-output-collector-idempotency.diff",
            jira_context_path=(
                "knowledge_packs/demo_team/docs/historical-jira/"
                "DFP-110-output-collection-idempotency.md"
            ),
            top_k=8,
        )
    )

    assert "## Related Codebase Memory" in response.markdown
    assert "OutputCollector.java" in response.markdown
    assert "INC-102" in response.markdown or "Duplicate output" in response.markdown
    assert "DFP-110" in response.markdown
    assert any("INC-102" in source or "DFP-110" in source for source in response.sources_used)
