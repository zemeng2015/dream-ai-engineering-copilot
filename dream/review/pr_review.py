# SPDX-License-Identifier: Apache-2.0

from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.codebase import CodebaseIndexRepository, CodebaseRetriever
from dream.codebase.models import CodebaseSearchResult, TestMapping
from dream.core.errors import AccessDeniedError, DreamError, NotFoundError
from dream.core.paths import (
    display_path,
    resolve_artifact_path,
    resolve_project_path,
)
from dream.graph import EvidenceGraphRepository, EvidenceGraphRetriever
from dream.graph.models import EvidenceGraphSearchResult
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.llm import BaseLLMProvider, MockLLMProvider
from dream.memory import MemoryClaimRetriever
from dream.memory.models import MemoryClaimRetrievalBatch, MemoryClaimSearchResult
from dream.memory.repository import MemoryDistillationRepository
from dream.review.diff_parser import parse_unified_diff
from dream.review.models import PRReviewRequest, PRReviewResponse
from dream.review.templates import render_pr_review_summary
from dream.security import AccessContext, DefaultAccessPolicy


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
        memory_repository: MemoryDistillationRepository | None = None,
        memory_claim_retriever: MemoryClaimRetriever | None = None,
        access_policy: DefaultAccessPolicy | None = None,
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
        self.memory_repository = memory_repository or MemoryDistillationRepository()
        self.memory_claim_retriever = memory_claim_retriever or MemoryClaimRetriever(
            repository=self.memory_repository
        )
        self.access_policy = access_policy or DefaultAccessPolicy()

    def review(
        self,
        request: PRReviewRequest,
        *,
        access_context: AccessContext | None = None,
    ) -> PRReviewResponse:
        context = access_context or AccessContext.public_demo(team_ids={request.team_id})
        self.access_policy.require(
            context=context,
            team_id=request.team_id,
            action="requirement_work",
            resource_access=request.access,
            resource_id="new-pr-review",
        )
        if context.mode == "private-extension" and (
            request.pr_diff_path or request.jira_context_path
        ):
            raise AccessDeniedError(
                "Private PR review accepts connector-supplied inline content only; "
                "local path inputs are disabled."
            )
        run_id = f"pr-{uuid4().hex[:12]}"
        diff_text = self._read_diff(request)
        diff_summary = parse_unified_diff(diff_text)
        jira_context = self._read_optional_context(
            request.jira_context_path, request.jira_context_text
        )

        pack = self.pack_loader.load(request.team_id)
        self.access_policy.require(
            context=context,
            team_id=request.team_id,
            action="retrieve",
            resource_access=pack.access,
            resource_id=f"knowledge-pack:{pack.team_id}",
        )
        pack_dir = self.pack_loader.pack_dir(pack.team_id)
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
            access_context=context,
        )
        warnings = []
        if not retrieved and (request.app or request.component):
            retrieved = SimpleRetriever(chunks).search(
                query,
                team_id=request.team_id,
                top_k=request.top_k,
                access_context=context,
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
            access_context=context,
        )
        warnings.extend(codebase_warnings)
        memory_batch = self._governed_memory_context(
            team_id=request.team_id,
            query=" ".join([query, *diff_summary.files_changed]),
            top_k=request.top_k,
            access_context=context,
        )
        warnings.extend(memory_batch.warnings)
        artifact_access = self.access_policy.derive_artifact_access(
            context=context,
            team_id=request.team_id,
            source_access=[
                *(chunk.access for chunk in retrieved),
                *(result.access for result in codebase_results),
                *(mapping.access for mapping in related_tests),
                *(result.claim.security.resource_access() for result in memory_batch.results),
            ],
            requested_access=request.access,
        )
        prompt = render_pr_review_summary(
            diff_summary=diff_summary,
            jira_context=jira_context,
            chunks=retrieved,
            codebase_results=codebase_results,
            related_tests=related_tests,
            memory_claims=memory_batch.results,
            warnings=warnings,
        )
        from dream.context import ContextIntelligenceService

        ContextIntelligenceService(
            codebase_repository=self.codebase_repository,
            graph_repository=self.graph_repository,
            memory_repository=self.memory_repository,
        ).save_pr_review_context(
            run_id=run_id,
            request=request,
            diff_summary=diff_summary,
            chunks=retrieved,
            codebase_results=codebase_results,
            related_tests=related_tests,
            memory_claims=memory_batch.results,
            warnings=warnings,
            prompt=prompt,
            access_context=context,
            artifact_access=artifact_access,
        )
        llm_response = self.llm_provider.complete(prompt)
        markdown = llm_response.text
        output_path = resolve_artifact_path(f"pr-review-summary-{run_id}.md")
        output_path.write_text(markdown, encoding="utf-8")
        sources_used = sorted(
            {chunk.source_path for chunk in retrieved}
            | {result.source_path for result in codebase_results}
            | {mapping.test_file for mapping in related_tests}
            | {
                source
                for result in memory_batch.results
                for source in self._memory_claim_sources(result)
            }
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
            memory_claims_used=[result.claim.claim_id for result in memory_batch.results],
            blocked_memory_claim_ids=memory_batch.blocked_claim_ids,
            context_trail_id=f"context-trail-{run_id}",
        )

    def _governed_memory_context(
        self,
        *,
        team_id: str,
        query: str,
        top_k: int,
        access_context: AccessContext,
    ) -> MemoryClaimRetrievalBatch:
        try:
            batch = self.memory_claim_retriever.search_with_policy(
                team_id=team_id,
                query=query,
                top_k=200,
                access_context=access_context,
            )
        except NotFoundError:
            return MemoryClaimRetrievalBatch(
                warnings=[
                    "No governed memory scan exists for this team; PR review used "
                    "document, codebase, and graph context only."
                ]
            )
        if batch.results:
            batch.results = sorted(
                batch.results,
                key=lambda item: (
                    0 if item.review_event is not None else 1,
                    -item.score,
                    item.claim.claim_id,
                ),
            )[: max(top_k, 8)]
        if not batch.results and not batch.warnings:
            batch.warnings.append("No policy-approved memory claim matched this PR review context.")
        return batch

    @staticmethod
    def _memory_claim_sources(result: MemoryClaimSearchResult) -> set[str]:
        return {
            f"memory-claim:{result.claim.claim_id}",
            *(span.path for span in result.claim.evidence.spans),
        }

    @staticmethod
    def _read_diff(request: PRReviewRequest) -> str:
        if request.pr_diff_text and request.pr_diff_text.strip():
            return request.pr_diff_text
        if request.pr_diff_path is None:
            raise DreamError("Either pr_diff_text or pr_diff_path is required.")
        diff_path = resolve_project_path(request.pr_diff_path, must_exist=True)
        return diff_path.read_text(encoding="utf-8")

    @staticmethod
    def _read_optional_context(
        path_value: str | None, inline_value: str | None = None
    ) -> str | None:
        if inline_value and inline_value.strip():
            return inline_value
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
        access_context: AccessContext,
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
            index=index,
            query=query,
            top_k=request.top_k,
            access_context=access_context,
        )
        changed_results: list[CodebaseSearchResult] = []
        related_tests: list[TestMapping] = []
        for changed_file in diff_summary.files_changed:
            file_node = self.codebase_retriever.find_file(
                team_id=request.team_id,
                repo_name=request.repo_name,
                file_path=changed_file,
                access_context=access_context,
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
                        access=file_node.access.model_copy(deep=True),
                    )
                )
                related_tests.extend(
                    self.codebase_retriever.find_tests_for_source(
                        team_id=request.team_id,
                        repo_name=request.repo_name,
                        source_file=file_node.path,
                        access_context=access_context,
                    )
                )
        merged = self._merge_results(changed_results + results)
        graph_results = self._graph_context(
            request=request,
            diff_summary=diff_summary,
            query=query,
            access_context=access_context,
        )
        merged = self._merge_results(merged + graph_results)
        return (
            merged[: request.top_k + len(changed_results) + 6],
            self._dedupe_tests(related_tests),
            [],
        )

    def _graph_context(
        self,
        *,
        request: PRReviewRequest,
        diff_summary,
        query: str,
        access_context: AccessContext,
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
            access_context=access_context,
        )
        for changed_file in diff_summary.files_changed:
            neighbors = self.graph_retriever.neighbors(
                team_id=request.team_id,
                repo_name=request.repo_name,
                node=changed_file,
                limit=8,
                access_context=access_context,
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
                    access=node.access.model_copy(deep=True),
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
