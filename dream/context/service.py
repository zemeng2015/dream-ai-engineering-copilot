# SPDX-License-Identifier: Apache-2.0

import re
from collections import Counter
from uuid import uuid4

from dream.codebase.repository import CodebaseIndexRepository
from dream.context.models import (
    ContextPack,
    EvidenceCandidate,
    EvidenceCard,
    GraphPathReference,
    MemoryClaimReference,
    MemoryMapReport,
    PromptPreview,
    RetrievalStep,
    RetrievalTrail,
)
from dream.context.repository import ContextArtifactRepository
from dream.extensions import DefaultRedactionProvider
from dream.graph import EvidenceGraphRepository, EvidenceGraphRetriever
from dream.knowledge.models import Chunk
from dream.memory.claim_retriever import MemoryClaimRetriever
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases.models import ContextEvidence, RequirementCaseSnapshot
from dream.requirement_cases.repository import RequirementCaseRepository
from dream.requirement_cases.templates import (
    render_engineering_brief,
    render_engineering_brief_prompt,
    render_jira_draft,
    render_jira_draft_prompt,
)
from dream.review.diff_parser import DiffSummary

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")
STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "when",
    "which",
    "that",
    "this",
    "want",
    "wants",
    "users",
    "user",
    "still",
    "takes",
    "too",
    "long",
}


class ContextIntelligenceService:
    def __init__(
        self,
        *,
        repository: ContextArtifactRepository | None = None,
        requirement_repository: RequirementCaseRepository | None = None,
        graph_repository: EvidenceGraphRepository | None = None,
        memory_repository: MemoryDistillationRepository | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
    ) -> None:
        self.repository = repository or ContextArtifactRepository()
        self.requirement_repository = requirement_repository or RequirementCaseRepository()
        self.graph_repository = graph_repository or EvidenceGraphRepository()
        self.graph_retriever = EvidenceGraphRetriever(repository=self.graph_repository)
        self.memory_repository = memory_repository or MemoryDistillationRepository()
        self.memory_retriever = MemoryClaimRetriever(repository=self.memory_repository)
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        self.redaction = DefaultRedactionProvider()

    def trace_case(self, case_id: str) -> RetrievalTrail:
        snapshot = self.requirement_repository.get(case_id)
        repo_name = self._default_repo_name(snapshot.case.team_id)
        selected = [_candidate_from_context(item, selected=True) for item in snapshot.evidence]
        concepts = _detect_concepts(snapshot.case.raw_request, selected)
        graph_paths = self._graph_paths(
            team_id=snapshot.case.team_id,
            repo_name=repo_name,
            query=snapshot.case.raw_request,
        )
        considered_claims = self._memory_claims(
            team_id=snapshot.case.team_id,
            query=snapshot.case.raw_request,
            include_candidates=True,
        )
        used_claims = [item for item in considered_claims if item.status == "approved"]
        trail = RetrievalTrail(
            trail_id=f"context-trail-{case_id}",
            case_id=case_id,
            team_id=snapshot.case.team_id,
            repo_name=repo_name,
            raw_query=snapshot.case.raw_request,
            detected_concepts=concepts,
            retrieval_steps=[
                RetrievalStep(
                    step_name="requirement_case_memory_search",
                    query=snapshot.case.raw_request,
                    provider="EngineeringMemoryRetriever",
                    candidates_found=len(snapshot.evidence),
                    selected_count=len(selected),
                    notes=["Reused analyzed Requirement Case evidence."],
                ),
                RetrievalStep(
                    step_name="graph_expansion",
                    query=snapshot.case.raw_request,
                    provider="EvidenceGraphRetriever",
                    candidates_found=len(graph_paths),
                    selected_count=len(graph_paths),
                ),
                RetrievalStep(
                    step_name="memory_claim_review",
                    query=snapshot.case.raw_request,
                    provider="MemoryClaimRetriever",
                    candidates_found=len(considered_claims),
                    selected_count=len(used_claims),
                ),
            ],
            candidate_evidence=selected,
            selected_evidence=selected,
            excluded_evidence=[],
            ranking_reasons=sorted({item.reason for item in selected}),
            graph_expansion_paths=graph_paths,
            memory_claims_considered=considered_claims,
            memory_claims_used=used_claims,
            warnings=snapshot.warnings,
            final_context_summary=_summary(selected, graph_paths, used_claims),
        )
        return self.repository.save_trail(trail)

    def assemble_case(self, case_id: str) -> ContextPack:
        snapshot = self.requirement_repository.get(case_id)
        trail = self.trace_case(case_id)
        return self._pack_from_snapshot(snapshot, trail)

    def prompt_for_case(self, case_id: str, target: str = "jira_draft") -> PromptPreview:
        snapshot = self.requirement_repository.get(case_id)
        pack = self.assemble_case(case_id)
        if target == "engineering_brief":
            deterministic = render_engineering_brief(
                case=snapshot.case,
                evidence=snapshot.evidence,
                impact_items=snapshot.impact_items,
                questions=snapshot.questions,
            )
            prompt = render_engineering_brief_prompt(
                case=snapshot.case,
                evidence=snapshot.evidence,
                impact_items=snapshot.impact_items,
                questions=snapshot.questions,
                deterministic_draft=deterministic,
            )
        else:
            deterministic = render_jira_draft(
                case=snapshot.case,
                evidence=snapshot.evidence,
                impact_items=snapshot.impact_items,
                questions=snapshot.questions,
            )
            prompt = render_jira_draft_prompt(
                case=snapshot.case,
                evidence=snapshot.evidence,
                impact_items=snapshot.impact_items,
                questions=snapshot.questions,
                deterministic_draft=deterministic,
            )
        preview = PromptPreview(
            preview_id=f"prompt-preview-{case_id}-{target}",
            case_id=case_id,
            target=target,
            provider_mode="mock-or-configured-provider",
            prompt_text=self.redaction.redact(prompt),
            evidence_paths=_pack_evidence_paths(pack),
            warnings=pack.warnings,
        )
        return self.repository.save_prompt_preview(preview)

    def save_pr_review_context(
        self,
        *,
        run_id: str,
        request,
        diff_summary: DiffSummary,
        chunks: list[Chunk],
        codebase_results,
        related_tests,
        warnings: list[str],
        prompt: str,
    ) -> tuple[RetrievalTrail, ContextPack, PromptPreview]:
        evidence = [_candidate_from_chunk(chunk) for chunk in chunks]
        evidence.extend(_candidate_from_codebase(result) for result in codebase_results)
        for mapping in related_tests:
            evidence.append(
                EvidenceCandidate(
                    evidence_id=f"test:{mapping.test_file}",
                    source_type="test_file",
                    title=mapping.test_file,
                    source_path=mapping.test_file,
                    excerpt=mapping.reason,
                    score=float(mapping.confidence * 10),
                    reason="Related test mapping from codebase memory.",
                    selected=True,
                    authority_status="candidate",
                )
            )
        concepts = _detect_concepts(diff_summary.rough_changed_content, evidence)
        graph_paths = self._graph_paths(
            team_id=request.team_id,
            repo_name=request.repo_name,
            query=" ".join([diff_summary.rough_changed_content, *diff_summary.files_changed]),
        )
        selected = [item.model_copy(update={"selected": True}) for item in evidence]
        trail = RetrievalTrail(
            trail_id=f"context-trail-{run_id}",
            run_id=run_id,
            review_id=run_id,
            team_id=request.team_id,
            repo_name=request.repo_name,
            raw_query=request.pr_diff_path or "inline PR diff",
            detected_concepts=concepts,
            retrieval_steps=[
                RetrievalStep(
                    step_name="pr_document_search",
                    query=diff_summary.rough_changed_content,
                    provider="SimpleRetriever",
                    candidates_found=len(chunks),
                    selected_count=len(chunks),
                ),
                RetrievalStep(
                    step_name="pr_codebase_and_graph_expansion",
                    query=" ".join(diff_summary.files_changed),
                    provider="CodebaseRetriever/EvidenceGraphRetriever",
                    candidates_found=len(codebase_results) + len(related_tests),
                    selected_count=len(codebase_results) + len(related_tests),
                ),
            ],
            candidate_evidence=selected,
            selected_evidence=selected,
            excluded_evidence=[],
            ranking_reasons=sorted({item.reason for item in selected}),
            graph_expansion_paths=graph_paths,
            warnings=warnings,
            final_context_summary=_summary(selected, graph_paths, []),
        )
        trail = self.repository.save_trail(trail)
        pack = self._pack_from_candidates(
            context_pack_id=f"context-pack-{run_id}",
            team_id=request.team_id,
            repo_name=request.repo_name,
            user_request=request.pr_diff_path or "inline PR diff",
            run_id=run_id,
            candidates=selected,
            graph_paths=graph_paths,
            warnings=warnings,
        )
        preview = PromptPreview(
            preview_id=f"prompt-preview-{run_id}-pr_review",
            run_id=run_id,
            target="pr_review",
            provider_mode=request.llm_provider,
            prompt_text=self.redaction.redact(prompt),
            evidence_paths=_pack_evidence_paths(pack),
            warnings=warnings,
        )
        return trail, pack, self.repository.save_prompt_preview(preview)

    def evidence_card(self, *, team_id: str, source_path: str, repo_name: str | None = None):
        graph_results = self.graph_retriever.search(
            team_id=team_id,
            repo_name=repo_name,
            query=source_path,
            top_k=5,
        )
        matched = next(
            (item for item in graph_results if item.node.source_path == source_path),
            None,
        )
        if matched:
            node = matched.node
            related = [item.source_path or item.title for item in matched.connected_nodes]
            return EvidenceCard(
                card_id=f"evidence-card-{_safe_id(source_path)}",
                title=node.title,
                source_path=source_path,
                source_type=node.node_type,
                short_abstract=str(node.metadata.get("summary") or node.title),
                structured_overview=[
                    f"Graph score: {matched.score}",
                    f"Matched terms: {', '.join(matched.matched_terms) or 'path match'}",
                ],
                source_references=matched.evidence_paths,
                concepts=node.concepts,
                related_sources=related,
                authority_status="graph-backed",
                warnings=[],
            )
        return EvidenceCard(
            card_id=f"evidence-card-{_safe_id(source_path)}",
            title=source_path.split("/")[-1],
            source_path=source_path,
            source_type="unknown",
            short_abstract="Source is not present in the current evidence graph.",
            warnings=["No graph-backed metadata found for this source."],
        )

    def memory_report(self, *, team_id: str, repo_name: str | None = None) -> MemoryMapReport:
        graph = self.graph_repository.try_load(team_id, repo_name)
        top_concepts: list[str] = []
        most_connected: list[str] = []
        important_paths: list[str] = []
        missing_tests: list[str] = []
        warnings: list[str] = []
        if graph is None:
            warnings.append("No evidence graph found for this team/repo.")
        else:
            top_concepts = [node.title for node in graph.nodes if node.node_type == "concept"][:10]
            degree = Counter()
            node_by_id = {node.node_id: node for node in graph.nodes}
            for edge in graph.edges:
                degree[edge.from_node_id] += 1
                degree[edge.to_node_id] += 1
            most_connected = [
                node_by_id[node_id].source_path or node_by_id[node_id].title
                for node_id, _ in degree.most_common(10)
                if node_id in node_by_id
            ]
            explanation = self.graph_retriever.explain(
                team_id=team_id,
                repo_name=repo_name,
                query="execution status",
            )
            important_paths = explanation.evidence_paths[:10]
            indexed = self.codebase_repository.try_load(team_id, repo_name) if repo_name else None
            if indexed:
                mapped_sources = {mapping.source_file for mapping in indexed.tests}
                missing_tests = [
                    file.path
                    for file in indexed.files
                    if file.role == "source"
                    and file.language in {"java", "typescript", "python"}
                    and file.path not in mapped_sources
                ][:10]
        approved, candidate = self._claim_counts(team_id)
        report = MemoryMapReport(
            report_id=f"memory-map-{team_id}-{repo_name or '_team'}",
            team_id=team_id,
            repo_name=repo_name,
            top_concepts=top_concepts,
            most_connected_sources=most_connected,
            important_paths=important_paths,
            missing_test_links=missing_tests,
            approved_memory_claims=approved,
            candidate_memory_claims=candidate,
            warnings=warnings,
            recommendations=_memory_recommendations(warnings, missing_tests, candidate),
        )
        return self.repository.save_memory_report(report)

    def _pack_from_snapshot(
        self,
        snapshot: RequirementCaseSnapshot,
        trail: RetrievalTrail,
    ) -> ContextPack:
        return self._pack_from_candidates(
            context_pack_id=f"context-pack-{snapshot.case.case_id}",
            team_id=snapshot.case.team_id,
            repo_name=trail.repo_name,
            user_request=snapshot.case.raw_request,
            case_id=snapshot.case.case_id,
            candidates=trail.selected_evidence,
            graph_paths=trail.graph_expansion_paths,
            selected_claims=trail.memory_claims_used,
            candidate_claims=[
                item for item in trail.memory_claims_considered if item.status != "approved"
            ],
            warnings=trail.warnings,
        )

    def _pack_from_candidates(
        self,
        *,
        context_pack_id: str,
        team_id: str,
        repo_name: str | None,
        user_request: str,
        candidates: list[EvidenceCandidate],
        graph_paths: list[GraphPathReference],
        case_id: str | None = None,
        run_id: str | None = None,
        selected_claims: list[MemoryClaimReference] | None = None,
        candidate_claims: list[MemoryClaimReference] | None = None,
        warnings: list[str] | None = None,
    ) -> ContextPack:
        pack = ContextPack(
            context_pack_id=context_pack_id,
            case_id=case_id,
            run_id=run_id,
            review_id=run_id,
            team_id=team_id,
            repo_name=repo_name,
            user_request=user_request,
            selected_docs=_filter(
                candidates,
                {"knowledge_doc", "domain_doc", "architecture_doc", "runbook"},
            ),
            selected_code=_filter(candidates, {"code_file", "code_symbol", "concept"}),
            selected_tests=_filter(candidates, {"test_file", "testing_doc"}),
            selected_incidents=_filter(candidates, {"incident", "graph_incident"}),
            selected_historical_jira=_filter(
                candidates, {"historical_jira", "graph_historical_jira"}
            ),
            selected_historical_pr=_filter(candidates, {"historical_pr", "graph_historical_pr"}),
            selected_memory_claims=selected_claims or [],
            candidate_memory_claims=candidate_claims or [],
            excluded_evidence=[item for item in candidates if not item.selected],
            graph_paths=graph_paths,
            selected_evidence_count=len([item for item in candidates if item.selected]),
            warnings=warnings or [],
        )
        return self.repository.save_context_pack(pack)

    def _graph_paths(
        self,
        *,
        team_id: str,
        repo_name: str | None,
        query: str,
    ) -> list[GraphPathReference]:
        explanation = self.graph_retriever.explain(
            team_id=team_id,
            repo_name=repo_name,
            query=query,
        )
        return [
            GraphPathReference(
                query=query,
                path=path,
                source_paths=[
                    node.source_path
                    for node in explanation.matched_nodes
                    if node.source_path and node.title in path
                ],
            )
            for path in explanation.evidence_paths
        ]

    def _memory_claims(
        self,
        *,
        team_id: str,
        query: str,
        include_candidates: bool,
    ) -> list[MemoryClaimReference]:
        try:
            scan = self.memory_repository.load_scan(team_id, "latest")
        except Exception:  # noqa: BLE001 - missing memory scan should not break context trace.
            return []
        review_statuses = self.memory_repository.latest_review_statuses(team_id)
        terms = set(_tokens(query))
        refs: list[MemoryClaimReference] = []
        for claim in scan.claims:
            effective = review_statuses.get(claim.claim_id)
            status = effective.new_status if effective else claim.governance.status
            if status != "approved" and not include_candidates:
                continue
            claim_terms = set(
                _tokens(
                    " ".join(
                        [
                            claim.entity.canonical_name,
                            " ".join(claim.entity.aliases),
                            claim.relation.type,
                            claim.relation.value or "",
                            " ".join(span.path for span in claim.evidence.spans),
                        ]
                    )
                )
            )
            if terms and not terms.intersection(claim_terms):
                continue
            refs.append(
                MemoryClaimReference(
                    claim_id=claim.claim_id,
                    status=status,
                    entity=claim.entity.canonical_name,
                    relation=claim.relation.type,
                    value=claim.relation.value or claim.relation.object_entity_id,
                    evidence_paths=[span.path for span in claim.evidence.spans],
                    intake_proofs=claim.evidence.intake_proofs,
                    reason="Memory claim matched request terms.",
                )
            )
        refs.sort(key=lambda ref: (0 if ref.intake_proofs else 1, ref.entity, ref.claim_id))
        return refs[:20]

    def _claim_counts(self, team_id: str) -> tuple[int, int]:
        try:
            scan = self.memory_repository.load_scan(team_id, "latest")
        except Exception:  # noqa: BLE001
            return 0, 0
        review_statuses = self.memory_repository.latest_review_statuses(team_id)
        approved = 0
        candidate = 0
        for claim in scan.claims:
            effective = review_statuses.get(claim.claim_id)
            status = effective.new_status if effective else claim.governance.status
            if status == "approved":
                approved += 1
            elif status == "candidate":
                candidate += 1
        return approved, candidate

    def _default_repo_name(self, team_id: str) -> str | None:
        repo_names = self.codebase_repository.list_repo_names(team_id)
        return repo_names[0] if repo_names else None


def _candidate_from_context(item: ContextEvidence, *, selected: bool) -> EvidenceCandidate:
    source_type = _normalize_source_type(item.source_type, item.source_path)
    return EvidenceCandidate(
        evidence_id=item.evidence_id,
        source_type=source_type,
        title=item.title,
        source_path=item.source_path,
        excerpt=item.excerpt,
        score=item.relevance_score,
        reason=item.reason,
        selected=selected,
        concepts=_detect_concepts(" ".join([item.title, item.excerpt, item.source_path]), []),
        authority_status=_authority_for_source_type(source_type),
    )


def _candidate_from_chunk(chunk: Chunk) -> EvidenceCandidate:
    source_type = _normalize_source_type(
        str(chunk.metadata.get("doc_type") or "knowledge_doc"),
        chunk.source_path,
    )
    return EvidenceCandidate(
        evidence_id=f"doc:{chunk.id}",
        source_type=source_type,
        title=chunk.title,
        source_path=chunk.source_path,
        excerpt=" ".join(chunk.content.split())[:500],
        score=10.0,
        reason="Knowledge pack chunk matched PR review query.",
        selected=True,
        concepts=_detect_concepts(chunk.content, []),
        authority_status="knowledge_pack",
    )


def _candidate_from_codebase(result) -> EvidenceCandidate:
    source_type = _normalize_source_type(result.result_type, result.source_path)
    return EvidenceCandidate(
        evidence_id=f"{result.result_type}:{result.source_path}:{result.title}",
        source_type=source_type,
        title=result.title,
        source_path=result.source_path,
        excerpt=result.excerpt,
        score=float(result.score),
        reason=result.reason,
        selected=True,
        concepts=_detect_concepts(" ".join([result.title, result.excerpt, result.source_path]), []),
        authority_status=_authority_for_source_type(source_type),
    )


def _detect_concepts(raw_text: str, evidence: list[EvidenceCandidate]) -> list[str]:
    tokens = [
        token.lower().replace("_", "-")
        for token in TOKEN_RE.findall(raw_text)
        if len(token) > 2 and token.lower() not in STOP_WORDS
    ]
    for item in evidence:
        tokens.extend(item.concepts)
        tokens.extend(_tokens(item.title))
    phrases = {
        "execution status": ["execution", "status"],
        "task status": ["task", "status"],
        "stuck running": ["stuck", "running"],
        "output collection": ["output", "collection"],
        "partial recovery": ["partial", "recovery"],
        "runbook": ["runbook"],
        "idempotency": ["idempotency"],
    }
    detected = {
        name
        for name, required in phrases.items()
        if all(term in tokens for term in required)
    }
    common = [item for item, _ in Counter(tokens).most_common(8) if item not in STOP_WORDS]
    return sorted(detected | set(common[:6]))


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]


def _authority_for_source_type(source_type: str) -> str:
    if source_type in {"code_file", "code_symbol", "test_file"}:
        return "deterministic"
    if source_type.startswith("graph_"):
        return "graph-backed"
    if source_type in {"incident", "historical_jira", "historical_pr"}:
        return "knowledge_pack"
    return "unknown"


def _normalize_source_type(source_type: str, source_path: str) -> str:
    normalized_path = source_path.lower().replace("\\", "/")
    if "docs/incidents/" in normalized_path:
        return "incident"
    if "docs/historical-jira/" in normalized_path:
        return "historical_jira"
    if "docs/historical-pr/" in normalized_path:
        return "historical_pr"
    if "docs/testing/" in normalized_path:
        return "testing_doc"
    if "docs/architecture/" in normalized_path:
        return "architecture_doc"
    if "docs/domain/" in normalized_path:
        return "domain_doc"
    if "docs/runbooks/" in normalized_path:
        return "runbook"
    return source_type


def _summary(
    selected: list[EvidenceCandidate],
    graph_paths: list[GraphPathReference],
    claims: list[MemoryClaimReference],
) -> str:
    types = Counter(item.source_type for item in selected)
    type_summary = ", ".join(f"{key}={value}" for key, value in sorted(types.items()))
    return (
        f"Selected {len(selected)} evidence items ({type_summary or 'none'}), "
        f"{len(graph_paths)} graph paths, and {len(claims)} approved memory claims."
    )


def _filter(items: list[EvidenceCandidate], prefixes: set[str]) -> list[EvidenceCandidate]:
    return [
        item
        for item in items
        if item.selected
        and (
            item.source_type in prefixes
            or any(item.source_type.startswith(f"{prefix}_") for prefix in prefixes)
            or any(prefix in item.source_path.lower() for prefix in prefixes)
        )
    ]


def _pack_evidence_paths(pack: ContextPack) -> list[str]:
    values = []
    for group in [
        pack.selected_docs,
        pack.selected_code,
        pack.selected_tests,
        pack.selected_incidents,
        pack.selected_historical_jira,
        pack.selected_historical_pr,
    ]:
        values.extend(item.source_path for item in group)
    values.extend(path for claim in pack.selected_memory_claims for path in claim.evidence_paths)
    return sorted(dict.fromkeys(values))


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")[:80] or uuid4().hex[:12]


def _memory_recommendations(
    warnings: list[str],
    missing_tests: list[str],
    candidate_claims: int,
) -> list[str]:
    recommendations = []
    if warnings:
        recommendations.append("Build or refresh the Evidence Graph Lite artifact.")
    if missing_tests:
        recommendations.append("Add or verify source-to-test mappings for high-value files.")
    if candidate_claims:
        recommendations.append("Review candidate memory claims before relying on them as context.")
    return recommendations or ["Memory map is ready for the current demo scope."]
