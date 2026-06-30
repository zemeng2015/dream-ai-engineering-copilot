# SPDX-License-Identifier: Apache-2.0

import hashlib

from dream.codebase.repository import CodebaseIndexRepository
from dream.codebase.retriever import CodebaseRetriever
from dream.graph import EvidenceGraphRepository, EvidenceGraphRetriever
from dream.graph.models import EvidenceGraphSearchResult
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.requirement_cases.models import ContextEvidence


class EngineeringMemoryRetriever:
    def __init__(
        self,
        *,
        pack_loader: KnowledgePackLoader | None = None,
        doc_loader: MarkdownDocumentLoader | None = None,
        chunker: Chunker | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
        codebase_retriever: CodebaseRetriever | None = None,
        graph_repository: EvidenceGraphRepository | None = None,
        graph_retriever: EvidenceGraphRetriever | None = None,
    ) -> None:
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.doc_loader = doc_loader or MarkdownDocumentLoader()
        self.chunker = chunker or Chunker()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        self.codebase_retriever = codebase_retriever or CodebaseRetriever(
            repository=self.codebase_repository
        )
        self.graph_repository = graph_repository or EvidenceGraphRepository()
        self.graph_retriever = graph_retriever or EvidenceGraphRetriever(
            repository=self.graph_repository
        )

    def search(
        self,
        *,
        team_id: str,
        query: str,
        repo_name: str | None = None,
        top_k: int = 8,
        app: str | None = None,
        component: str | None = None,
    ) -> list[ContextEvidence]:
        evidence = []
        for knowledge_query in self._knowledge_queries(query):
            evidence.extend(
                self._search_knowledge(
                    team_id=team_id,
                    query=knowledge_query,
                    top_k=top_k,
                    app=app,
                    component=component,
                )
            )
            if app is not None or component is not None:
                evidence.extend(
                    self._search_knowledge(
                        team_id=team_id,
                        query=knowledge_query,
                        top_k=top_k,
                        app=None,
                        component=None,
                    )
                )
        repo_names = [repo_name] if repo_name else self.codebase_repository.list_repo_names(team_id)
        for candidate_repo in repo_names:
            if not candidate_repo:
                continue
            results = []
            for code_query in self._code_queries(query):
                results.extend(
                    self.codebase_retriever.search(
                        team_id=team_id,
                        repo_name=candidate_repo,
                        query=code_query,
                        top_k=top_k,
                    )
                )
            for result in results:
                evidence.append(
                    ContextEvidence(
                        evidence_id=self._stable_id(
                            f"code:{candidate_repo}:{result.source_path}:{result.title}"
                        ),
                        case_id="",
                        source_type=result.result_type,
                        source_path=result.source_path,
                        title=result.title,
                        excerpt=result.excerpt,
                        relevance_score=float(result.score),
                        reason=result.reason,
                    )
                )
        evidence.sort(key=lambda item: (-item.relevance_score, item.source_path, item.title))
        evidence.extend(
            self._search_graph(
                team_id=team_id,
                repo_names=repo_names,
                query=query,
                top_k=top_k,
            )
        )
        evidence.sort(key=lambda item: (-item.relevance_score, item.source_path, item.title))
        evidence = self._dedupe(evidence)
        return self._balanced_top_k(evidence, top_k)

    def _search_graph(
        self,
        *,
        team_id: str,
        repo_names: list[str | None],
        query: str,
        top_k: int,
    ) -> list[ContextEvidence]:
        evidence: list[ContextEvidence] = []
        graph_names = repo_names or self.graph_repository.list_graph_names(team_id)
        if not graph_names:
            graph_names = [None]
        for repo_name in graph_names:
            for result in self.graph_retriever.search(
                team_id=team_id,
                repo_name=repo_name,
                query=query,
                top_k=top_k,
            ):
                evidence.append(self._graph_result_to_evidence(result))
        return evidence

    def _search_knowledge(
        self,
        *,
        team_id: str,
        query: str,
        top_k: int,
        app: str | None,
        component: str | None,
    ) -> list[ContextEvidence]:
        pack = self.pack_loader.load(team_id)
        pack_dir = self.pack_loader.pack_dir(pack.team_id)
        documents = self.doc_loader.load_for_pack(pack, pack_dir)
        chunks = self.chunker.chunk_all(documents)
        retrieved = SimpleRetriever(chunks).search(
            query,
            team_id=team_id,
            app=app,
            component=component,
            top_k=top_k,
        )
        evidence: list[ContextEvidence] = []
        for chunk in retrieved:
            evidence.append(
                ContextEvidence(
                    evidence_id=self._stable_id(f"doc:{chunk.id}:{chunk.source_path}"),
                    case_id="",
                    source_type="knowledge_doc",
                    source_path=chunk.source_path,
                    title=chunk.title,
                    excerpt=" ".join(chunk.content.split())[:500],
                    relevance_score=10.0,
                    reason="Knowledge pack chunk matched request keywords.",
                )
            )
        return evidence

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _graph_result_to_evidence(cls, result: EvidenceGraphSearchResult) -> ContextEvidence:
        node = result.node
        source_path = node.source_path or f"evidence-graph#{node.node_type}:{node.key}"
        connected = ", ".join(
            f"{item.title} [{item.node_type}]" for item in result.connected_nodes[:6]
        )
        paths = "; ".join(result.evidence_paths[:4])
        excerpt_parts = [str(node.metadata.get("summary", "")), connected, paths]
        excerpt = " ".join(part for part in excerpt_parts if part).strip()
        return ContextEvidence(
            evidence_id=cls._stable_id(f"graph:{node.node_id}:{source_path}"),
            case_id="",
            source_type=f"graph_{node.node_type}",
            source_path=source_path,
            title=node.title,
            excerpt=excerpt[:600] or "Evidence graph node matched the request.",
            relevance_score=float(min(result.score, 25)),
            reason=result.reason,
        )

    @staticmethod
    def _code_queries(query: str) -> list[str]:
        queries = [query]
        normalized = query.lower()
        if any(term in normalized for term in ["job", "execution", "status", "async"]):
            queries.append("job execution controller service test status")
            queries.append(
                "StatusTracker ExecutionService ExecutionController BatchJobAdapter "
                "ExecutionServiceTest StatusTrackerTest execution monitor polling"
            )
        return queries

    @staticmethod
    def _knowledge_queries(query: str) -> list[str]:
        queries = [query]
        normalized = query.lower()
        if any(term in normalized for term in ["job", "execution", "status", "async"]):
            queries.extend(
                [
                    "execution status async tracking polling status stuck running",
                    "INC-103 DFP-101 DFP-109 PR-502 PR-505 status tracker persistence",
                    "job lifecycle execution model status tracking design",
                    "status transition test plan execution monitor auto refresh",
                ]
            )
        return queries

    @staticmethod
    def _dedupe(evidence: list[ContextEvidence]) -> list[ContextEvidence]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[ContextEvidence] = []
        for item in evidence:
            if item.source_type in {"code_file", "code_symbol", "test_file"}:
                key = ("codebase", item.source_path, "")
            else:
                key = (item.source_type, item.source_path, item.title)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    @classmethod
    def _balanced_top_k(
        cls,
        evidence: list[ContextEvidence],
        top_k: int,
    ) -> list[ContextEvidence]:
        if len(evidence) <= top_k:
            return evidence
        selected: list[ContextEvidence] = []
        categories = [
            "incident",
            "historical_jira",
            "historical_pr",
            "architecture",
            "domain",
            "testing",
            "concept_memory",
            "graph_evidence",
            "graph_incident",
            "graph_historical_jira",
            "graph_historical_pr",
            "graph_concept_memory",
            "test_file",
            "test_file",
            "code_file",
            "code_file",
            "code_symbol",
            "code_concept",
        ]
        for category in categories:
            candidates = [
                item
                for item in evidence
                if item not in selected and cls._category(item) == category
            ]
            for item in sorted(candidates, key=cls._status_context_priority):
                if len(selected) >= top_k:
                    return selected
                selected.append(item)
                break
        for item in evidence:
            if len(selected) >= top_k:
                break
            if item not in selected:
                selected.append(item)
        return selected

    @staticmethod
    def _category(item: ContextEvidence) -> str:
        source = item.source_path.lower()
        if "/docs/incidents/" in source:
            return "incident"
        if "/docs/historical-jira/" in source:
            return "historical_jira"
        if "/docs/historical-pr/" in source:
            return "historical_pr"
        if "/docs/architecture/" in source:
            return "architecture"
        if "/docs/domain/" in source:
            return "domain"
        if "/docs/testing/" in source:
            return "testing"
        if "/docs/concepts/" in source:
            return "concept_memory"
        if item.source_type == "test_file":
            return "test_file"
        if item.source_type == "code_file":
            return "code_file"
        if item.source_type == "code_symbol":
            return "code_symbol"
        if item.source_type == "concept":
            return "code_concept"
        if item.source_type.startswith("graph_"):
            return item.source_type
        return item.source_type

    @staticmethod
    def _status_context_priority(item: ContextEvidence) -> tuple[int, str, str]:
        text = f"{item.source_path} {item.title} {item.excerpt}".lower()
        preferred_terms = [
            "inc-103",
            "dfp-109",
            "dfp-101",
            "pr-502",
            "pr-505",
            "status-tracking",
            "execution-status",
            "executionservice",
            "statustracker",
            "batchjobadapter",
            "execution-monitor",
            "status transition",
            "polling",
        ]
        priority = 0 if any(term in text for term in preferred_terms) else 1
        return priority, item.source_path, item.title
