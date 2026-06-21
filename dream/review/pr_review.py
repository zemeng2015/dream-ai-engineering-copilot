# SPDX-License-Identifier: Apache-2.0

from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.codebase import CodebaseIndexRepository, CodebaseRetriever
from dream.codebase.models import CodebaseSearchResult, TestMapping
from dream.core.paths import (
    KNOWLEDGE_PACKS_DIR,
    display_path,
    ensure_artifacts_dir,
    resolve_project_path,
)
from dream.graph import EvidenceGraphRepository, EvidenceGraphRetriever
from dream.graph.models import EvidenceGraphSearchResult
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.llm import BaseLLMProvider, MockLLMProvider
from dream.review.diff_parser import parse_unified_diff
from dream.review.models import PRReviewRequest, PRReviewResponse
from dream.review.templates import render_pr_review_summary


class PRReviewAssistant:
    def __init__(
        self,
        *,
        pack_loader: KnowledgePackLoader | None = None,
        doc_loader: MarkdownDocumentLoader | None = None,
        chunker: Chunker | None = None,
        llm_provider: BaseLLMProvider | None = None,
        audit_logger: AuditLogger | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
        codebase_retriever: CodebaseRetriever | None = None,
        graph_repository: EvidenceGraphRepository | None = None,
        graph_retriever: EvidenceGraphRetriever | None = None,
    ) -> None:
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.doc_loader = doc_loader or MarkdownDocumentLoader()
        self.chunker = chunker or Chunker()
        self.llm_provider = llm_provider or MockLLMProvider()
        self.audit_logger = audit_logger or AuditLogger()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        self.codebase_retriever = codebase_retriever or CodebaseRetriever(
            repository=self.codebase_repository
        )
        self.graph_repository = graph_repository or EvidenceGraphRepository()
        self.graph_retriever = graph_retriever or EvidenceGraphRetriever(
            repository=self.graph_repository
        )

    def review(self, request: PRReviewRequest) -> PRReviewResponse:
        run_id = f"pr-{uuid4().hex[:12]}"
        diff_path = resolve_project_path(request.pr_diff_path, must_exist=True)
        diff_text = diff_path.read_text(encoding="utf-8")
        diff_summary = parse_unified_diff(diff_text)
        jira_context = self._read_optional_context(request.jira_context_path)

        pack = self.pack_loader.load(request.team_id)
        pack_dir = KNOWLEDGE_PACKS_DIR / pack.team_id
        documents = self.doc_loader.load_for_pack(pack, pack_dir)
        chunks = self.chunker.chunk_all(documents)
        query = " ".join(
            [
                diff_summary.rough_changed_content,
                jira_context or "",
                " ".join(pack.review_rules),
            ]
        )
        retrieved = SimpleRetriever(chunks).search(
            query,
            team_id=request.team_id,
            app=request.app,
            component=request.component,
            top_k=request.top_k,
        )
        warnings = []
        if not retrieved and (request.app or request.component):
            retrieved = SimpleRetriever(chunks).search(
                query,
                team_id=request.team_id,
                top_k=request.top_k,
            )
            if retrieved:
                warnings.append(
                    "No chunks matched the app/component filters; retried with team-level context."
                )
        if not retrieved:
            warnings.append("No matching knowledge chunks were retrieved.")
        codebase_results, related_tests, codebase_warnings = self._codebase_context(
            request=request,
            diff_summary=diff_summary,
            query=query,
        )
        warnings.extend(codebase_warnings)
        prompt = render_pr_review_summary(
            diff_summary=diff_summary,
            jira_context=jira_context,
            chunks=retrieved,
            codebase_results=codebase_results,
            related_tests=related_tests,
            warnings=warnings,
        )
        llm_response = self.llm_provider.complete(prompt)
        markdown = llm_response.text
        output_path = ensure_artifacts_dir() / f"pr-review-summary-{run_id}.md"
        output_path.write_text(markdown, encoding="utf-8")
        sources_used = sorted(
            {chunk.source_path for chunk in retrieved}
            | {result.source_path for result in codebase_results}
            | {mapping.test_file for mapping in related_tests}
        )
        self.audit_logger.log_generation(
            run_id=run_id,
            use_case="pr_review_summary",
            team_id=request.team_id,
            repo_name=request.repo_name,
            input_payload=request.model_dump(),
            retrieved_source_paths=sources_used,
            model_provider=llm_response.provider_name,
            model_name=llm_response.model_name,
            output_path=display_path(output_path),
            status="success",
            warnings=warnings,
        )
        return PRReviewResponse(
            run_id=run_id,
            markdown=markdown,
            sources_used=sources_used,
            warnings=warnings,
        )

    @staticmethod
    def _read_optional_context(path_value: str | None) -> str | None:
        if path_value is None:
            return None
        path = resolve_project_path(path_value, must_exist=True)
        return path.read_text(encoding="utf-8")

    def _codebase_context(
        self,
        *,
        request: PRReviewRequest,
        diff_summary,
        query: str,
    ) -> tuple[list[CodebaseSearchResult], list[TestMapping], list[str]]:
        if request.repo_name is None:
            return [], [], []
        index = self.codebase_repository.try_load(request.team_id, request.repo_name)
        if index is None:
            return (
                [],
                [],
                [
                    "No codebase index found for this repo/team. "
                    "Review used document and diff context only."
                ],
            )
        results = self.codebase_retriever.search_index(
            index=index, query=query, top_k=request.top_k
        )
        changed_results: list[CodebaseSearchResult] = []
        related_tests: list[TestMapping] = []
        for changed_file in diff_summary.files_changed:
            file_node = self.codebase_retriever.find_file(
                team_id=request.team_id,
                repo_name=request.repo_name,
                file_path=changed_file,
            )
            if file_node is not None:
                changed_results.append(
                    CodebaseSearchResult(
                        result_type="changed_file",
                        title=file_node.path,
                        source_path=file_node.path,
                        excerpt=file_node.summary or "",
                        score=100,
                        reason="File was directly changed in the PR diff.",
                        metadata={"role": file_node.role, "language": file_node.language},
                    )
                )
                related_tests.extend(
                    self.codebase_retriever.find_tests_for_source(
                        team_id=request.team_id,
                        repo_name=request.repo_name,
                        source_file=file_node.path,
                    )
                )
        merged = self._merge_results(changed_results + results)
        graph_results = self._graph_context(
            request=request,
            diff_summary=diff_summary,
            query=query,
        )
        merged = self._merge_results(merged + graph_results)
        return merged[: request.top_k + len(changed_results) + 6], self._dedupe_tests(
            related_tests
        ), []

    def _graph_context(
        self,
        *,
        request: PRReviewRequest,
        diff_summary,
        query: str,
    ) -> list[CodebaseSearchResult]:
        if request.repo_name is None:
            return []
        if self.graph_repository.try_load(request.team_id, request.repo_name) is None:
            return []
        graph_query = " ".join([query, " ".join(diff_summary.files_changed)])
        results = self.graph_retriever.search(
            team_id=request.team_id,
            repo_name=request.repo_name,
            query=graph_query,
            top_k=request.top_k,
        )
        for changed_file in diff_summary.files_changed:
            neighbors = self.graph_retriever.neighbors(
                team_id=request.team_id,
                repo_name=request.repo_name,
                node=changed_file,
                limit=8,
            )
            for node in neighbors.matched_nodes:
                if node.key == changed_file or node.source_path == changed_file:
                    continue
                results.append(
                    EvidenceGraphSearchResult(
                        node=node,
                        score=20,
                        reason="Evidence graph neighbor of a directly changed file.",
                        matched_terms=[],
                        connected_nodes=[],
                        evidence_paths=neighbors.evidence_paths,
                    )
                )
        return self._graph_results_to_codebase_results(results)

    @staticmethod
    def _graph_results_to_codebase_results(
        results: list[EvidenceGraphSearchResult],
    ) -> list[CodebaseSearchResult]:
        converted: list[CodebaseSearchResult] = []
        for result in results:
            node = result.node
            source_path = node.source_path or f"evidence-graph#{node.node_type}:{node.key}"
            connected = ", ".join(
                f"{item.title} [{item.node_type}]" for item in result.connected_nodes[:5]
            )
            paths = "; ".join(result.evidence_paths[:3])
            excerpt = " ".join(part for part in [connected, paths] if part).strip()
            converted.append(
                CodebaseSearchResult(
                    result_type=f"graph_{node.node_type}",
                    title=node.title,
                    source_path=source_path,
                    excerpt=excerpt or "Evidence graph matched this PR context.",
                    score=result.score,
                    reason=result.reason,
                    metadata={"graph_node_type": node.node_type},
                )
            )
        return converted

    @staticmethod
    def _merge_results(results: list[CodebaseSearchResult]) -> list[CodebaseSearchResult]:
        seen: set[tuple[str, str]] = set()
        merged: list[CodebaseSearchResult] = []
        for result in sorted(results, key=lambda item: (-item.score, item.source_path, item.title)):
            key = (result.result_type, result.source_path)
            if key not in seen:
                seen.add(key)
                merged.append(result)
        return merged

    @staticmethod
    def _dedupe_tests(mappings: list[TestMapping]) -> list[TestMapping]:
        seen: set[tuple[str, str]] = set()
        deduped: list[TestMapping] = []
        for mapping in mappings:
            key = (mapping.source_file, mapping.test_file)
            if key not in seen:
                seen.add(key)
                deduped.append(mapping)
        return deduped
