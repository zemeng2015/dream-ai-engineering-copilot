# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase.models import FileNode, RepoIndex
from dream.codebase.repository import CodebaseIndexRepository
from dream.codebase.retriever import CodebaseRetriever
from dream.graph.models import EvidenceEdge, EvidenceGraph, EvidenceNode
from dream.graph.retriever import EvidenceGraphRetriever
from dream.knowledge.models import Chunk
from dream.knowledge.retriever import SimpleRetriever
from dream.memory import MemoryClaimRetriever, MemoryDistillationService
from dream.memory.repository import MemoryDistillationRepository
from dream.security import AccessContext, RequestPrincipal, ResourceAccess


def _access(group_id: str) -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_group_ids={group_id},
        source_acl_version=f"acl-{group_id}-v1",
    )


def _context(group_id: str) -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id=f"user-{group_id}",
            authenticated=True,
            team_ids={"team-a"},
            group_ids={group_id},
            roles={"viewer", "author"},
        ),
    )


def test_knowledge_retriever_never_returns_cross_acl_chunks() -> None:
    chunks = [
        Chunk(
            id="allowed",
            document_id="doc-a",
            source_path="allowed.md",
            title="Status architecture",
            content="status tracker allowed evidence",
            metadata={"team_id": "team-a"},
            access=_access("engineering-a"),
        ),
        Chunk(
            id="denied",
            document_id="doc-b",
            source_path="denied.md",
            title="Status architecture secret",
            content="status tracker forbidden evidence",
            metadata={"team_id": "team-a"},
            access=_access("engineering-b"),
        ),
    ]

    results = SimpleRetriever(chunks).search(
        "status tracker",
        team_id="team-a",
        access_context=_context("engineering-a"),
    )

    assert [item.id for item in results] == ["allowed"]
    assert all("forbidden" not in item.content for item in results)


def test_codebase_and_graph_retrievers_remove_denied_nodes_and_paths() -> None:
    allowed_file = FileNode(
        file_id="file-a",
        path="src/AllowedStatus.java",
        language="java",
        size_bytes=10,
        line_count=1,
        role="source",
        summary="status tracker allowed",
        access=_access("engineering-a"),
    )
    denied_file = FileNode(
        file_id="file-b",
        path="src/RestrictedStatus.java",
        language="java",
        size_bytes=10,
        line_count=1,
        role="source",
        summary="status tracker forbidden",
        access=_access("engineering-b"),
    )
    index = RepoIndex(
        repo_id="repo-a",
        repo_name="repo-a",
        repo_path="examples/java-demo-repo",
        team_id="team-a",
        indexed_at="2026-07-10T00:00:00Z",
        files=[allowed_file, denied_file],
        summary="mixed ACL index",
        access=_access("engineering-a"),
    )
    code_results = CodebaseRetriever().search_index(
        index=index,
        query="status tracker",
        top_k=10,
        access_context=_context("engineering-a"),
    )

    allowed_node = EvidenceNode(
        node_id="node-a",
        node_type="code_file",
        key=allowed_file.path,
        title="Allowed status",
        source_path=allowed_file.path,
        access=_access("engineering-a"),
    )
    denied_node = EvidenceNode(
        node_id="node-b",
        node_type="incident",
        key="restricted-incident",
        title="Restricted status incident",
        source_path="docs/restricted-incident.md",
        access=_access("engineering-b"),
    )
    graph = EvidenceGraph(
        graph_id="graph-a",
        team_id="team-a",
        built_at="2026-07-10T00:00:00Z",
        nodes=[allowed_node, denied_node],
        edges=[
            EvidenceEdge(
                edge_id="edge-a-b",
                from_node_id="node-a",
                to_node_id="node-b",
                edge_type="RELATED_TO",
                confidence=1.0,
                reason="test edge",
            )
        ],
        summary="mixed ACL graph",
    )
    graph_results = EvidenceGraphRetriever().search_graph(
        graph=graph,
        query="status",
        top_k=10,
        access_context=_context("engineering-a"),
    )

    assert [item.source_path for item in code_results] == [allowed_file.path]
    assert [item.node.node_id for item in graph_results] == ["node-a"]
    assert graph_results[0].connected_nodes == []
    assert graph_results[0].evidence_paths == []


def test_memory_claim_retrieval_enforces_propagated_source_acl(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    memory_repository = MemoryDistillationRepository(artifacts_dir)
    service = MemoryDistillationService(
        repository=memory_repository,
        codebase_repository=CodebaseIndexRepository(artifacts_dir),
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
    )
    service.scan(
        team_id="team-a",
        repo_path="examples/java-demo-repo",
        repo_name="repo-a",
        access=_access("engineering-a"),
    )
    retriever = MemoryClaimRetriever(repository=memory_repository)

    allowed = retriever.search(
        team_id="team-a",
        query="AsyncJobStatusTracker",
        top_k=20,
        access_context=_context("engineering-a"),
    )
    denied = retriever.search(
        team_id="team-a",
        query="AsyncJobStatusTracker",
        top_k=20,
        access_context=_context("engineering-b"),
    )

    assert allowed
    assert all(item.claim.security.allowed_group_ids == ["engineering-a"] for item in allowed)
    assert denied == []
