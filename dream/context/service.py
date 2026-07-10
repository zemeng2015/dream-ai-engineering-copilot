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
from dream.memory.models import MemoryClaimSearchResult
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
from dream.security import AccessContext, DefaultAccessPolicy
from dream.security.models import ResourceAccess

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
        access_policy: DefaultAccessPolicy | None = None,
    ) -> None:
        self.repository = repository or ContextArtifactRepository()
        self.requirement_repository = requirement_repository or RequirementCaseRepository()
        self.graph_repository = graph_repository or EvidenceGraphRepository()
        self.access_policy = access_policy or DefaultAccessPolicy()
        self.graph_retriever = EvidenceGraphRetriever(
            repository=self.graph_repository,
            access_policy=self.access_policy,
        )
        self.memory_repository = memory_repository or MemoryDistillationRepository()
        self.memory_retriever = MemoryClaimRetriever(
            repository=self.memory_repository,
            access_policy=self.access_policy,
        )
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        self.redaction = DefaultRedactionProvider()

    def load_trail(
        self,
        trail_id: str,
        *,
        access_context: AccessContext,
    ) -> RetrievalTrail:
        trail = self.repository.load_trail(trail_id)
        self.access_policy.require(
            context=access_context,
            team_id=trail.team_id,
            action="retrieve",
            resource_access=trail.access,
            resource_id=trail.trail_id,
        )
        return trail

    def load_context_pack(
        self,
        context_pack_id: str,
        *,
        access_context: AccessContext,
    ) -> ContextPack:
        pack = self.repository.load_context_pack(context_pack_id)
        self.access_policy.require(
            context=access_context,
            team_id=pack.team_id,
            action="retrieve",
            resource_access=pack.access,
            resource_id=pack.context_pack_id,
        )
        return pack

    def load_prompt_preview(
        self,
        preview_id: str,
        *,
        access_context: AccessContext,
    ) -> PromptPreview:
        preview = self.repository.load_prompt_preview(preview_id)
        self.access_policy.require(
            context=access_context,
            team_id=preview.team_id,
            action="retrieve",
            resource_access=preview.access,
            resource_id=preview.preview_id,
        )
        return preview

    def trace_case(
        self,
        case_id: str,
        *,
        access_context: AccessContext | None = None,
    ) -> RetrievalTrail:
        snapshot = self.requirement_repository.get(case_id)
        context = access_context or AccessContext.public_demo(team_ids={snapshot.case.team_id})
        self.access_policy.require(
            context=context,
            team_id=snapshot.case.team_id,
            action="retrieve",
            resource_access=snapshot.case.access,
            resource_id=snapshot.case.case_id,
        )
        repo_name = self._default_repo_name(
            snapshot.case.team_id,
            access_context=context,
        )
        selected = [
            _candidate_from_context(item, selected=True)
            for item in snapshot.evidence
            if self.access_policy.decide(
                context=context,
                team_id=snapshot.case.team_id,
                action="retrieve",
                resource_access=item.access,
                resource_id=item.evidence_id,
            ).allowed
        ]
        concepts = _detect_concepts(snapshot.case.raw_request, selected)
        graph_paths = self._graph_paths(
            team_id=snapshot.case.team_id,
            repo_name=repo_name,
            query=snapshot.case.raw_request,
            access_context=context,
        )
        considered_claims = self._memory_claims(
            team_id=snapshot.case.team_id,
            query=snapshot.case.raw_request,
            include_candidates=True,
            access_context=context,
        )
        used_claims, claim_policy_warnings = self._approved_memory_claims(
            team_id=snapshot.case.team_id,
            query=snapshot.case.raw_request,
            access_context=context,
        )
        used_claim_ids = {item.claim_id for item in used_claims}
        considered_claims = [
            *used_claims,
            *(item for item in considered_claims if item.claim_id not in used_claim_ids),
        ]
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
            warnings=list(dict.fromkeys([*snapshot.warnings, *claim_policy_warnings])),
            final_context_summary=_summary(selected, graph_paths, used_claims),
            access=snapshot.case.access.model_copy(deep=True),
        )
        return self.repository.save_trail(trail)

    def assemble_case(
        self,
        case_id: str,
        *,
        access_context: AccessContext | None = None,
    ) -> ContextPack:
        snapshot = self.requirement_repository.get(case_id)
        trail = self.trace_case(case_id, access_context=access_context)
        return self._pack_from_snapshot(snapshot, trail)

    def prompt_for_case(
        self,
        case_id: str,
        target: str = "jira_draft",
        *,
        access_context: AccessContext | None = None,
    ) -> PromptPreview:
        snapshot = self.requirement_repository.get(case_id)
        pack = self.assemble_case(case_id, access_context=access_context)
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
            team_id=snapshot.case.team_id,
            case_id=case_id,
            target=target,
            provider_mode="mock-or-configured-provider",
            prompt_text=self.redaction.redact(prompt),
            evidence_paths=_pack_evidence_paths(pack),
            warnings=pack.warnings,
            access=snapshot.case.access.model_copy(deep=True),
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
        memory_claims: list[MemoryClaimSearchResult],
        warnings: list[str],
        prompt: str,
        access_context: AccessContext | None = None,
        artifact_access: ResourceAccess | None = None,
    ) -> tuple[RetrievalTrail, ContextPack, PromptPreview]:
        context = access_context or AccessContext.public_demo(team_ids={request.team_id})
        output_access = artifact_access or request.access
        self.access_policy.require(
            context=context,
            team_id=request.team_id,
            action="retrieve",
            resource_access=request.access,
            resource_id=run_id,
        )
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
                    access=mapping.access.model_copy(deep=True),
                )
            )
        concepts = _detect_concepts(diff_summary.rough_changed_content, evidence)
        graph_paths = self._graph_paths(
            team_id=request.team_id,
            repo_name=request.repo_name,
            query=" ".join([diff_summary.rough_changed_content, *diff_summary.files_changed]),
            access_context=context,
        )
        claim_refs = [
            self._memory_claim_reference(
                result.claim,
                status=result.effective_status,
                reason=result.reason,
                reviewed_by=result.review_event.reviewer if result.review_event else None,
                reviewed_at=result.review_event.reviewed_at if result.review_event else None,
            )
            for result in memory_claims
        ]
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
                RetrievalStep(
                    step_name="pr_governed_memory_search",
                    query=" ".join(
                        [diff_summary.rough_changed_content, *diff_summary.files_changed]
                    ),
                    provider="MemoryClaimRetriever",
                    candidates_found=len(memory_claims),
                    selected_count=len(memory_claims),
                    notes=["Only policy-approved, conflict-free claims can be selected."],
                ),
            ],
            candidate_evidence=selected,
            selected_evidence=selected,
            excluded_evidence=[],
            ranking_reasons=sorted({item.reason for item in selected}),
            graph_expansion_paths=graph_paths,
            memory_claims_considered=claim_refs,
            memory_claims_used=claim_refs,
            warnings=warnings,
            final_context_summary=_summary(selected, graph_paths, claim_refs),
            access=output_access.model_copy(deep=True),
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
            selected_claims=claim_refs,
            warnings=warnings,
            access=output_access,
        )
        preview = PromptPreview(
            preview_id=f"prompt-preview-{run_id}-pr_review",
            team_id=request.team_id,
            run_id=run_id,
            target="pr_review",
            provider_mode=request.llm_provider,
            prompt_text=self.redaction.redact(prompt),
            evidence_paths=_pack_evidence_paths(pack),
            warnings=warnings,
            access=output_access.model_copy(deep=True),
        )
        return trail, pack, self.repository.save_prompt_preview(preview)

    def evidence_card(
        self,
        *,
        team_id: str,
        source_path: str,
        repo_name: str | None = None,
        access_context: AccessContext | None = None,
    ):
        context = access_context or AccessContext.public_demo(team_ids={team_id})
        graph_results = self.graph_retriever.search(
            team_id=team_id,
            repo_name=repo_name,
            query=source_path,
            top_k=5,
            access_context=context,
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
                access=node.access.model_copy(deep=True),
            )
        return EvidenceCard(
            card_id=f"evidence-card-{_safe_id(source_path)}",
            title=source_path.split("/")[-1],
            source_path=source_path,
            source_type="unknown",
            short_abstract="Source is not present in the current evidence graph.",
            warnings=["No graph-backed metadata found for this source."],
        )

    def memory_report(
        self,
        *,
        team_id: str,
        repo_name: str | None = None,
        access_context: AccessContext | None = None,
    ) -> MemoryMapReport:
        context = access_context or AccessContext.public_demo(team_ids={team_id})
        graph = self.graph_repository.try_load(team_id, repo_name)
        top_concepts: list[str] = []
        most_connected: list[str] = []
        important_paths: list[str] = []
        missing_tests: list[str] = []
        warnings: list[str] = []
        visible_access: list[ResourceAccess] = []
        if graph is None:
            warnings.append("No evidence graph found for this team/repo.")
        else:
            readable_nodes = [
                node
                for node in graph.nodes
                if self.access_policy.decide(
                    context=context,
                    team_id=team_id,
                    action="retrieve",
                    resource_access=node.access,
                    resource_id=node.node_id,
                ).allowed
            ]
            visible_access.extend(node.access for node in readable_nodes)
            top_concepts = [node.title for node in readable_nodes if node.node_type == "concept"][
                :10
            ]
            degree = Counter()
            node_by_id = {node.node_id: node for node in readable_nodes}
            for edge in graph.edges:
                if edge.from_node_id not in node_by_id or edge.to_node_id not in node_by_id:
                    continue
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
                access_context=context,
            )
            important_paths = explanation.evidence_paths[:10]
            indexed = self.codebase_repository.try_load(team_id, repo_name) if repo_name else None
            if indexed:
                if not self.access_policy.decide(
                    context=context,
                    team_id=team_id,
                    action="retrieve",
                    resource_access=indexed.access,
                    resource_id=indexed.repo_id,
                ).allowed:
                    indexed = None
            if indexed:
                mapped_sources = {mapping.source_file for mapping in indexed.tests}
                missing_tests = [
                    file.path
                    for file in indexed.files
                    if self.access_policy.decide(
                        context=context,
                        team_id=team_id,
                        action="retrieve",
                        resource_access=file.access,
                        resource_id=file.file_id,
                    ).allowed
                    and file.role == "source"
                    and file.language in {"java", "typescript", "python"}
                    and file.path not in mapped_sources
                ][:10]
        approved, candidate = self._claim_counts(team_id, access_context=context)
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
            access=self._aggregate_access(visible_access, context=context),
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
            access=snapshot.case.access,
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
        access: ResourceAccess | None = None,
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
            access=(access or ResourceAccess()).model_copy(deep=True),
        )
        return self.repository.save_context_pack(pack)

    def _graph_paths(
        self,
        *,
        team_id: str,
        repo_name: str | None,
        query: str,
        access_context: AccessContext,
    ) -> list[GraphPathReference]:
        explanation = self.graph_retriever.explain(
            team_id=team_id,
            repo_name=repo_name,
            query=query,
            access_context=access_context,
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
        access_context: AccessContext,
    ) -> list[MemoryClaimReference]:
        try:
            scan = self.memory_repository.load_scan(team_id, "latest")
        except Exception:  # noqa: BLE001 - missing memory scan should not break context trace.
            return []
        review_statuses = self.memory_repository.latest_review_statuses(team_id)
        terms = set(_tokens(query))
        refs: list[MemoryClaimReference] = []
        for claim in scan.claims:
            if not self.access_policy.decide(
                context=access_context,
                team_id=team_id,
                action="retrieve",
                resource_access=claim.security.resource_access(),
                resource_id=claim.claim_id,
            ).allowed:
                continue
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
                self._memory_claim_reference(
                    claim,
                    status=status,
                    reason="Memory claim matched request terms.",
                )
            )
        refs.sort(key=lambda ref: (0 if ref.intake_proofs else 1, ref.entity, ref.claim_id))
        return refs[:20]

    def _approved_memory_claims(
        self,
        *,
        team_id: str,
        query: str,
        access_context: AccessContext,
    ) -> tuple[list[MemoryClaimReference], list[str]]:
        try:
            batch = self.memory_retriever.search_with_policy(
                team_id=team_id,
                query=query,
                top_k=20,
                access_context=access_context,
            )
        except Exception:  # noqa: BLE001 - a missing scan must not break context trace.
            return [], []
        return [
            self._memory_claim_reference(
                result.claim,
                status=result.effective_status,
                reason=result.reason,
                reviewed_by=result.review_event.reviewer if result.review_event else None,
                reviewed_at=result.review_event.reviewed_at if result.review_event else None,
            )
            for result in batch.results
        ], batch.warnings

    @staticmethod
    def _memory_claim_reference(
        claim,
        *,
        status: str,
        reason: str,
        reviewed_by: str | None = None,
        reviewed_at: str | None = None,
    ) -> MemoryClaimReference:
        return MemoryClaimReference(
            claim_id=claim.claim_id,
            status=status,
            entity=claim.entity.canonical_name,
            relation=claim.relation.type,
            value=claim.relation.value or claim.relation.object_entity_id,
            evidence_paths=[span.path for span in claim.evidence.spans],
            intake_proofs=claim.evidence.intake_proofs,
            reason=reason,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            access=claim.security.resource_access(),
        )

    def _claim_counts(
        self,
        team_id: str,
        *,
        access_context: AccessContext,
    ) -> tuple[int, int]:
        try:
            scan = self.memory_repository.load_scan(team_id, "latest")
        except Exception:  # noqa: BLE001
            return 0, 0
        review_statuses = self.memory_repository.latest_review_statuses(team_id)
        approved = 0
        candidate = 0
        for claim in scan.claims:
            if not self.access_policy.decide(
                context=access_context,
                team_id=team_id,
                action="retrieve",
                resource_access=claim.security.resource_access(),
                resource_id=claim.claim_id,
            ).allowed:
                continue
            effective = review_statuses.get(claim.claim_id)
            status = effective.new_status if effective else claim.governance.status
            if status == "approved":
                approved += 1
            elif status == "candidate":
                candidate += 1
        return approved, candidate

    @staticmethod
    def _aggregate_access(
        descriptors: list[ResourceAccess],
        *,
        context: AccessContext,
    ) -> ResourceAccess:
        if not descriptors:
            return (
                ResourceAccess()
                if context.mode == "public-demo"
                else ResourceAccess.unscoped_private()
            )
        merged = descriptors[0].model_copy(deep=True)
        for descriptor in descriptors[1:]:
            merged = merged.restrictive_merge(descriptor)
        return merged

    def _default_repo_name(
        self,
        team_id: str,
        *,
        access_context: AccessContext,
    ) -> str | None:
        repo_names = self.codebase_repository.list_repo_names(team_id)
        for repo_name in repo_names:
            index = self.codebase_repository.try_load(team_id, repo_name)
            if (
                index is not None
                and self.access_policy.decide(
                    context=access_context,
                    team_id=team_id,
                    action="retrieve",
                    resource_access=index.access,
                    resource_id=index.repo_id,
                ).allowed
            ):
                return repo_name
        return None


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
        access=item.access.model_copy(deep=True),
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
        access=chunk.access.model_copy(deep=True),
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
        access=result.access.model_copy(deep=True),
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
        name for name, required in phrases.items() if all(term in tokens for term in required)
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
