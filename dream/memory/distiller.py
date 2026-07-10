# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from dream.audit.logger import AuditLogger
from dream.audit.models import AuditRecord
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository
from dream.codebase.models import SymbolNode, TestMapping
from dream.core.errors import DreamError, PathTraversalError
from dream.core.paths import PROJECT_ROOT, display_path, resolve_project_path
from dream.intake.models import IntakeDocument, KnowledgeDraft
from dream.intake.repository import IntakeRepository
from dream.knowledge import KnowledgePackLoader
from dream.memory.models import (
    ClaimAuditInfo,
    ExtractionInfo,
    GovernanceInfo,
    MemoryClaim,
    MemoryConflictClaimSide,
    MemoryConflictPair,
    MemoryConflictReport,
    MemoryConflictResolutionEvent,
    MemoryDiffResult,
    MemoryEntity,
    MemoryEvidence,
    MemoryEvidenceSpan,
    MemoryIntakeProof,
    MemoryIntakeSectionProof,
    MemoryRelation,
    MemoryReviewClaimSnapshot,
    MemoryReviewEvent,
    MemoryReviewFieldDiff,
    MemoryReviewSignalExplanation,
    MemoryScanResult,
    MemoryValidationSummary,
    RepoProvenanceInfo,
    SecurityInfo,
    SourceRecord,
    SourceSpan,
)
from dream.memory.repository import MemoryDistillationRepository

STRUCTURAL_EXTRACTION = "deterministic_structure"
SEMANTIC_EXTRACTION = "heuristic_semantic"
EXTRACTOR_VERSION = "memory-distillation-v0"
MEMORY_SCAN_SCHEMA_VERSION = "memory-scan-v0.3"
REVIEWABLE_STATUSES = {"candidate", "approved", "rejected", "quarantined"}
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,}", flags=re.IGNORECASE)
MATCH_STOP_WORDS = {
    "and",
    "app",
    "architecture",
    "component",
    "demo_team",
    "domain",
    "docs",
    "documented_by",
    "for",
    "incidents",
    "knowledge",
    "knowledge_packs",
    "md",
    "packs",
    "runbooks",
    "team",
    "testing",
    "the",
    "with",
}
CONFLICT_SINGLE_VALUED_RELATIONS = {
    "current_policy",
    "has_language",
    "has_owner",
    "has_status",
    "retention_policy",
    "security_classification",
    "sla",
}
CONFLICT_RESOLUTION_ACTIONS = {"approve_winner_reject_other"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|private[_-]?key)\s*[:=]")
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|token|private[_-]?key)(\s*[:=]\s*)([^\s,;\"']+)"
)
AWS_ACCESS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
PEM_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


@dataclass(frozen=True)
class _DocEntry:
    path: Path
    source_path: str
    metadata: dict[str, Any]
    content: str
    title: str
    doc_type: str


class MemoryDistillationService:
    def __init__(
        self,
        *,
        repository: MemoryDistillationRepository | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
        intake_repository: IntakeRepository | None = None,
        pack_loader: KnowledgePackLoader | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.repository = repository or MemoryDistillationRepository()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository(
            self.repository.artifacts_dir
        )
        self.intake_repository = intake_repository or IntakeRepository()
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.audit_logger = audit_logger or AuditLogger()

    def scan(
        self,
        *,
        team_id: str,
        repo_path: str | Path,
        repo_name: str | None = None,
        scan_id: str | None = None,
        created_at: str | None = None,
    ) -> MemoryScanResult:
        created_at = created_at or datetime.now(UTC).isoformat()
        scan_id = scan_id or f"memscan-{uuid4().hex[:12]}"
        root = resolve_project_path(repo_path, must_exist=True)
        provenance = self._repo_provenance(root)
        index = CodebaseIndexer(
            repository=self.codebase_repository,
            audit_logger=self.audit_logger,
        ).index(team_id=team_id, repo_path=root, repo_name=repo_name)

        sources: list[SourceRecord] = []
        claims: list[MemoryClaim] = []
        warnings: list[str] = []
        source_by_path: dict[str, tuple[SourceRecord, str]] = {}
        intake_proofs_by_path = self._intake_proofs_by_promoted_path(team_id)

        for file_node in index.files:
            path = root / file_node.path
            content = self._read_text(path)
            source = self._source_record(
                team_id=team_id,
                repo_name=index.repo_name,
                source_type=self._file_source_type(file_node.role),
                path=file_node.path,
                content=content,
                indexed_at=created_at,
                trust_level="high",
                commit_sha=provenance.commit_sha,
            )
            sources.append(source)
            source_by_path[file_node.path] = (source, content)
            span = source.spans[0]
            claims.append(
                self._claim(
                    team_id=team_id,
                    repo_name=index.repo_name,
                    scan_id=scan_id,
                    created_at=created_at,
                    entity_type="code_file" if file_node.role != "test" else "test",
                    entity_name=file_node.path,
                    relation_type="has_language",
                    value=file_node.language,
                    source=source,
                    span=span,
                    method=STRUCTURAL_EXTRACTION,
                    confidence=0.95,
                    status="approved",
                    risk_level="low",
                )
            )

        for symbol in index.symbols:
            source_tuple = source_by_path.get(symbol.file_path)
            if source_tuple is None:
                source, content = self._missing_source(
                    team_id,
                    index.repo_name,
                    symbol.file_path,
                    created_at,
                    provenance.commit_sha,
                )
                sources.append(source)
                source_by_path[symbol.file_path] = (source, content)
                warnings.append(f"Symbol source missing from codebase index: {symbol.file_path}")
            else:
                source, content = source_tuple
            span = self._span_for_symbol(source, content, symbol)
            claims.append(
                self._claim(
                    team_id=team_id,
                    repo_name=index.repo_name,
                    scan_id=scan_id,
                    created_at=created_at,
                    entity_type="endpoint" if symbol.kind == "endpoint" else "symbol",
                    entity_name=symbol.name,
                    relation_type="defined_in",
                    object_entity_id=self._entity_id("code_file", symbol.file_path),
                    value=symbol.signature or symbol.kind,
                    source=source,
                    span=span,
                    method=STRUCTURAL_EXTRACTION,
                    confidence=0.95,
                    status="approved",
                    risk_level="low",
                    aliases=[f"{symbol.file_path}#{symbol.name}"],
                )
            )
            if symbol.kind == "endpoint":
                claims.append(
                    self._claim(
                        team_id=team_id,
                        repo_name=index.repo_name,
                        scan_id=scan_id,
                        created_at=created_at,
                        entity_type="endpoint",
                        entity_name=symbol.name,
                        relation_type="implements",
                        value="endpoint-like method",
                        condition="direct code annotation",
                        source=source,
                        span=span,
                        method=STRUCTURAL_EXTRACTION,
                        confidence=0.9,
                        status="approved",
                        risk_level="low",
                        aliases=[f"{symbol.file_path}#{symbol.name}"],
                    )
                )

        for mapping in index.tests:
            source_tuple = source_by_path.get(mapping.source_file)
            if source_tuple is None:
                continue
            source, _ = source_tuple
            span = source.spans[0]
            claims.append(
                self._test_mapping_claim(
                    team_id=team_id,
                    repo_name=index.repo_name,
                    scan_id=scan_id,
                    created_at=created_at,
                    mapping=mapping,
                    source=source,
                    span=span,
                )
            )

        try:
            doc_entries = self._load_doc_entries(team_id)
        except DreamError as exc:
            doc_entries = []
            warnings.append(str(exc))
        for entry in doc_entries:
            intake_proof = intake_proofs_by_path.get(self._normalize_source_path(entry.source_path))
            doc_source = self._source_record(
                team_id=team_id,
                repo_name=index.repo_name,
                source_type=self._doc_source_type(entry),
                path=entry.source_path,
                content=entry.content,
                indexed_at=created_at,
                trust_level=self._doc_trust_level(entry),
                commit_sha=provenance.commit_sha,
            )
            sources.append(doc_source)
            claims.extend(
                self._doc_claims(
                    team_id=team_id,
                    repo_name=index.repo_name,
                    scan_id=scan_id,
                    created_at=created_at,
                    entry=entry,
                    source=doc_source,
                    intake_proof=intake_proof,
                )
            )

        claims = self._dedupe_claims(claims)
        validation = self._validate(sources=sources, claims=claims)
        scan = MemoryScanResult(
            schema_version=MEMORY_SCAN_SCHEMA_VERSION,
            scan_id=scan_id,
            team_id=team_id,
            repo_name=index.repo_name,
            created_at=created_at,
            provenance=provenance,
            sources=sources,
            claims=claims,
            validation=validation,
            summary=(
                f"Memory scan {scan_id} captured {len(sources)} sources and "
                f"{len(claims)} source-backed memory claims for {team_id}/{index.repo_name}."
            ),
            warnings=warnings + validation.warnings,
        )
        self.repository.save_scan(scan)
        return scan

    def diff(
        self,
        *,
        team_id: str,
        scan_id: str = "latest",
        base_scan_id: str | None = None,
    ) -> MemoryDiffResult:
        scan = self.repository.load_scan(team_id, scan_id)
        base = (
            self.repository.load_scan(team_id, base_scan_id)
            if base_scan_id
            else self.repository.previous_scan(team_id, scan.scan_id)
        )
        if base is None:
            markdown = self._review_queue_markdown(scan)
            return MemoryDiffResult(
                team_id=team_id,
                scan_id=scan.scan_id,
                base_scan_id=None,
                added_claims=scan.claims,
                unchanged_count=0,
                markdown=markdown,
            )

        base_by_id = {claim.claim_id: claim for claim in base.claims}
        current_by_id = {claim.claim_id: claim for claim in scan.claims}
        added = [claim for claim_id, claim in current_by_id.items() if claim_id not in base_by_id]
        removed = [claim for claim_id, claim in base_by_id.items() if claim_id not in current_by_id]
        changed = [
            claim
            for claim_id, claim in current_by_id.items()
            if claim_id in base_by_id
            and self._claim_compare_key(claim) != self._claim_compare_key(base_by_id[claim_id])
        ]
        unchanged = len(current_by_id) - len(added) - len(changed)
        markdown = self._diff_markdown(
            scan=scan,
            base=base,
            added=sorted(added, key=lambda item: item.claim_id),
            removed=sorted(removed, key=lambda item: item.claim_id),
            changed=sorted(changed, key=lambda item: item.claim_id),
            unchanged=unchanged,
        )
        return MemoryDiffResult(
            team_id=team_id,
            scan_id=scan.scan_id,
            base_scan_id=base.scan_id,
            added_claims=sorted(added, key=lambda item: item.claim_id),
            removed_claims=sorted(removed, key=lambda item: item.claim_id),
            changed_claims=sorted(changed, key=lambda item: item.claim_id),
            unchanged_count=unchanged,
            markdown=markdown,
        )

    def diff_markdown(
        self,
        *,
        team_id: str,
        scan_id: str = "latest",
        base_scan_id: str | None = None,
    ) -> str:
        return self.diff(team_id=team_id, scan_id=scan_id, base_scan_id=base_scan_id).markdown

    def conflicts(
        self,
        *,
        team_id: str,
        scan_id: str = "latest",
    ) -> MemoryConflictReport:
        scan = self.repository.load_scan(team_id, scan_id)
        latest_by_claim = self.repository.latest_review_statuses(team_id)
        active_claims = [
            claim
            for claim in scan.claims
            if self._effective_review_status(claim, latest_by_claim) in {"candidate", "approved"}
        ]
        pairs: list[MemoryConflictPair] = []
        for index, left in enumerate(sorted(active_claims, key=lambda item: item.claim_id)):
            if not self._is_conflict_review_relation(left.relation.type):
                continue
            left_value = _relation_compare_value(left)
            for right in active_claims[index + 1 :]:
                if right.entity.entity_id != left.entity.entity_id:
                    continue
                if right.relation.type != left.relation.type:
                    continue
                right_value = _relation_compare_value(right)
                if right_value == left_value:
                    continue
                pairs.append(
                    self._conflict_pair(
                        scan=scan,
                        left=left,
                        right=right,
                        latest_by_claim=latest_by_claim,
                    )
                )
        return MemoryConflictReport(
            team_id=team_id,
            scan_id=scan.scan_id,
            generated_at=datetime.now(UTC).isoformat(),
            conflict_count=len(pairs),
            pairs=sorted(pairs, key=lambda pair: pair.conflict_id),
        )

    def resolve_conflict(
        self,
        *,
        team_id: str,
        conflict_id: str,
        winning_claim_id: str,
        action: str = "approve_winner_reject_other",
        reviewer: str | None = None,
        reason: str | None = None,
        scan_id: str = "latest",
    ) -> MemoryConflictResolutionEvent:
        if action not in CONFLICT_RESOLUTION_ACTIONS:
            raise DreamError(f"Unsupported memory conflict resolution action: {action}")
        report = self.conflicts(team_id=team_id, scan_id=scan_id)
        pair = next(
            (item for item in report.pairs if item.conflict_id == conflict_id),
            None,
        )
        if pair is None:
            raise DreamError(f"Memory conflict not found: {team_id}/{scan_id}/{conflict_id}")
        claim_ids = {pair.left.claim.claim_id, pair.right.claim.claim_id}
        if winning_claim_id not in claim_ids:
            raise DreamError(
                f"Winning claim {winning_claim_id} is not part of conflict {conflict_id}"
            )
        rejected_claim_id = next(claim_id for claim_id in claim_ids if claim_id != winning_claim_id)
        reason_text = reason or (
            f"Resolved {conflict_id} by selecting {winning_claim_id} as durable memory."
        )
        winner_event = self.review_claim(
            team_id=team_id,
            claim_id=winning_claim_id,
            new_status="approved",
            reviewer=reviewer,
            reason=f"{reason_text} Winner for conflict {conflict_id}.",
            scan_id=pair.scan_id,
        )
        rejected_event = self.review_claim(
            team_id=team_id,
            claim_id=rejected_claim_id,
            new_status="rejected",
            reviewer=reviewer,
            reason=(
                f"{reason_text} Rejected in favor of {winning_claim_id} for conflict {conflict_id}."
            ),
            scan_id=pair.scan_id,
        )
        resolved_at = datetime.now(UTC).isoformat()
        review_event_ids = [winner_event.event_id, rejected_event.event_id]
        event = MemoryConflictResolutionEvent(
            event_id=f"memory-conflict-resolution-{uuid4().hex[:12]}",
            team_id=team_id,
            scan_id=pair.scan_id,
            conflict_id=conflict_id,
            action=action,
            winning_claim_id=winning_claim_id,
            rejected_claim_id=rejected_claim_id,
            reviewer=reviewer,
            reason=reason_text,
            resolved_at=resolved_at,
            reviewer_signature=self._conflict_resolution_signature(
                pair=pair,
                action=action,
                winning_claim_id=winning_claim_id,
                rejected_claim_id=rejected_claim_id,
                reviewer=reviewer,
                reason=reason_text,
                resolved_at=resolved_at,
                review_event_ids=review_event_ids,
            ),
            review_event_ids=review_event_ids,
            conflict_snapshot=pair,
        )
        self.repository.append_conflict_resolution_event(event)
        return event

    def review_claim(
        self,
        *,
        team_id: str,
        claim_id: str,
        new_status: str,
        reviewer: str | None = None,
        reason: str | None = None,
        scan_id: str = "latest",
    ) -> MemoryReviewEvent:
        if new_status not in REVIEWABLE_STATUSES:
            raise DreamError(f"Unsupported memory review status: {new_status}")
        scan = self.repository.load_scan(team_id, scan_id)
        claim = next((item for item in scan.claims if item.claim_id == claim_id), None)
        if claim is None:
            raise DreamError(f"Memory claim not found in scan {scan.scan_id}: {claim_id}")
        latest = self.repository.latest_review_statuses(team_id).get(claim_id)
        previous_status = latest.new_status if latest else claim.governance.status
        reviewed_at = datetime.now(UTC).isoformat()
        snapshot = self._review_claim_snapshot(claim)
        field_diffs = self._review_field_diffs(
            claim=claim,
            latest=latest,
            previous_status=previous_status,
            new_status=new_status,
            reviewer=reviewer,
            reason=reason,
        )
        risk_signals = self._review_risk_signals(claim)
        conflict_signals = self._review_conflict_signals(claim=claim, scan=scan)
        signal_explanations = self._review_signal_explanations(
            risk_signals=risk_signals,
            conflict_signals=conflict_signals,
        )
        reviewer_signature = self._reviewer_signature(
            claim=claim,
            scan_id=scan.scan_id,
            previous_status=previous_status,
            new_status=new_status,
            reviewer=reviewer,
            reason=reason,
            reviewed_at=reviewed_at,
            field_diffs=field_diffs,
            signal_explanations=signal_explanations,
        )
        event = MemoryReviewEvent(
            event_id=f"memory-review-{uuid4().hex[:12]}",
            team_id=team_id,
            claim_id=claim_id,
            scan_id=scan.scan_id,
            previous_status=previous_status,
            new_status=new_status,
            reviewer=reviewer,
            reason=reason,
            reviewed_at=reviewed_at,
            reviewer_signature=reviewer_signature,
            field_diffs=field_diffs,
            claim_snapshot=snapshot,
            risk_signals=risk_signals,
            conflict_signals=conflict_signals,
            signal_explanations=signal_explanations,
        )
        self.repository.append_review_event(event)
        return event

    @staticmethod
    def _review_claim_snapshot(claim: MemoryClaim) -> MemoryReviewClaimSnapshot:
        return MemoryReviewClaimSnapshot(
            claim_id=claim.claim_id,
            entity_type=claim.entity.entity_type,
            entity_name=claim.entity.canonical_name,
            relation_type=claim.relation.type,
            relation_value=claim.relation.value or claim.relation.object_entity_id,
            extraction_method=claim.extraction.method,
            confidence=claim.extraction.confidence,
            risk_level=claim.governance.risk_level,
            security_classification=claim.security.classification,
            evidence_paths=[span.path for span in claim.evidence.spans],
            intake_document_ids=[proof.document_id for proof in claim.evidence.intake_proofs],
            source_hashes=[
                proof.source_hash for proof in claim.evidence.intake_proofs if proof.source_hash
            ],
        )

    @staticmethod
    def _review_field_diffs(
        *,
        claim: MemoryClaim,
        latest: MemoryReviewEvent | None,
        previous_status: str,
        new_status: str,
        reviewer: str | None,
        reason: str | None,
    ) -> list[MemoryReviewFieldDiff]:
        previous_reviewer = latest.reviewer if latest else claim.governance.reviewer
        previous_reason = latest.reason if latest else claim.governance.rejection_reason
        candidates = [
            ("governance.status", previous_status, new_status),
            ("governance.reviewer", previous_reviewer, reviewer),
            ("governance.rejection_reason", previous_reason, reason),
        ]
        return [
            MemoryReviewFieldDiff(field_path=field_path, before=before, after=after)
            for field_path, before, after in candidates
            if before != after
        ]

    @staticmethod
    def _review_risk_signals(claim: MemoryClaim) -> list[str]:
        signals: list[str] = []
        if claim.extraction.method == SEMANTIC_EXTRACTION:
            signals.append("semantic_claim_requires_human_review")
        if claim.governance.risk_level != "low":
            signals.append(f"risk_level:{claim.governance.risk_level}")
        if claim.security.classification != "public_demo":
            signals.append(f"security_classification:{claim.security.classification}")
        if not claim.evidence.spans:
            signals.append("missing_evidence_span")
        for proof in claim.evidence.intake_proofs:
            if proof.source_hash_verified is not True:
                signals.append(f"intake_source_hash_unverified:{proof.document_id}")
        return sorted(set(signals))

    @staticmethod
    def _review_conflict_signals(
        *,
        claim: MemoryClaim,
        scan: MemoryScanResult,
    ) -> list[str]:
        if not MemoryDistillationService._is_conflict_review_relation(claim.relation.type):
            return []
        claim_value = _relation_compare_value(claim)
        conflicts = []
        for other in scan.claims:
            if other.claim_id == claim.claim_id:
                continue
            if other.entity.entity_id != claim.entity.entity_id:
                continue
            if other.relation.type != claim.relation.type:
                continue
            other_value = _relation_compare_value(other)
            if other_value != claim_value:
                conflicts.append(f"potential_conflict:{other.claim_id}:{other_value or '_'}")
        return sorted(conflicts)

    @staticmethod
    def _is_conflict_review_relation(relation_type: str) -> bool:
        return relation_type in CONFLICT_SINGLE_VALUED_RELATIONS

    @staticmethod
    def _review_signal_explanations(
        *,
        risk_signals: list[str],
        conflict_signals: list[str],
    ) -> list[MemoryReviewSignalExplanation]:
        explanations = [
            MemoryDistillationService._risk_signal_explanation(signal) for signal in risk_signals
        ]
        explanations.extend(
            MemoryDistillationService._conflict_signal_explanation(signal)
            for signal in conflict_signals
        )
        return explanations

    @staticmethod
    def _risk_signal_explanation(signal: str) -> MemoryReviewSignalExplanation:
        if signal == "semantic_claim_requires_human_review":
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="risk",
                severity="warning",
                explanation=(
                    "This claim was produced by heuristic semantic extraction, "
                    "so it must be reviewed before it can be trusted as approved memory."
                ),
            )
        if signal.startswith("risk_level:"):
            risk_level = signal.split(":", 1)[1]
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="risk",
                severity="warning",
                explanation=(
                    f"The claim governance risk level is {risk_level}; reviewers "
                    "should confirm the source still represents current team guidance."
                ),
                evidence=[risk_level],
            )
        if signal.startswith("security_classification:"):
            classification = signal.split(":", 1)[1]
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="risk",
                severity="warning",
                explanation=(
                    f"The claim source is classified as {classification}; reviewers "
                    "should confirm it is safe to expose in downstream context."
                ),
                evidence=[classification],
            )
        if signal == "missing_evidence_span":
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="risk",
                severity="warning",
                explanation=(
                    "No evidence span is attached to this claim, so the claim cannot "
                    "be traced back to an exact source excerpt."
                ),
            )
        if signal.startswith("intake_source_hash_unverified:"):
            document_id = signal.split(":", 1)[1]
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="risk",
                severity="warning",
                explanation=(
                    f"The raw intake source hash for {document_id} was not verified "
                    "against the stored raw file during scan."
                ),
                evidence=[document_id],
            )
        return MemoryReviewSignalExplanation(
            signal=signal,
            category="risk",
            severity="info",
            explanation="A risk signal was recorded for this review event.",
        )

    @staticmethod
    def _conflict_signal_explanation(signal: str) -> MemoryReviewSignalExplanation:
        if signal.startswith("potential_conflict:"):
            claim_id, value = signal.removeprefix("potential_conflict:").rsplit(":", 1)
            return MemoryReviewSignalExplanation(
                signal=signal,
                category="conflict",
                severity="warning",
                explanation=(
                    "Another claim in the same scan has the same entity and relation "
                    "but a different value. Review both claims before approving either "
                    "as durable memory."
                ),
                evidence=[claim_id, value],
            )
        return MemoryReviewSignalExplanation(
            signal=signal,
            category="conflict",
            severity="info",
            explanation="A conflict signal was recorded for this review event.",
        )

    @staticmethod
    def _conflict_pair(
        *,
        scan: MemoryScanResult,
        left: MemoryClaim,
        right: MemoryClaim,
        latest_by_claim: dict[str, MemoryReviewEvent],
    ) -> MemoryConflictPair:
        left_value = _relation_compare_value(left)
        right_value = _relation_compare_value(right)
        conflict_digest = hashlib.sha256(
            "|".join([scan.scan_id, left.claim_id, right.claim_id]).encode("utf-8")
        ).hexdigest()[:12]
        return MemoryConflictPair(
            conflict_id=f"memory-conflict-{conflict_digest}",
            team_id=scan.team_id,
            scan_id=scan.scan_id,
            entity_id=left.entity.entity_id,
            entity_name=left.entity.canonical_name,
            entity_type=left.entity.entity_type,
            relation_type=left.relation.type,
            left=MemoryDistillationService._conflict_side(
                claim=left,
                latest=latest_by_claim.get(left.claim_id),
            ),
            right=MemoryDistillationService._conflict_side(
                claim=right,
                latest=latest_by_claim.get(right.claim_id),
            ),
            signal=MemoryReviewSignalExplanation(
                signal=f"potential_conflict_pair:{left.claim_id}:{right.claim_id}",
                category="conflict",
                severity="warning",
                explanation=(
                    "These claims share the same entity and relation but point to "
                    "different values, so they should be reviewed as a pair before "
                    "either side is treated as durable memory."
                ),
                evidence=[left.claim_id, left_value or "_", right.claim_id, right_value or "_"],
            ),
        )

    @staticmethod
    def _conflict_side(
        *,
        claim: MemoryClaim,
        latest: MemoryReviewEvent | None,
    ) -> MemoryConflictClaimSide:
        return MemoryConflictClaimSide(
            claim=claim,
            effective_status=latest.new_status if latest else claim.governance.status,
            relation_value=_relation_compare_value(claim) or None,
            evidence_paths=[span.path for span in claim.evidence.spans],
            intake_document_ids=[proof.document_id for proof in claim.evidence.intake_proofs],
            latest_review=latest,
        )

    @staticmethod
    def _effective_review_status(
        claim: MemoryClaim,
        latest_by_claim: dict[str, MemoryReviewEvent],
    ) -> str:
        latest = latest_by_claim.get(claim.claim_id)
        return latest.new_status if latest else claim.governance.status

    @staticmethod
    def _conflict_resolution_signature(
        *,
        pair: MemoryConflictPair,
        action: str,
        winning_claim_id: str,
        rejected_claim_id: str,
        reviewer: str | None,
        reason: str | None,
        resolved_at: str,
        review_event_ids: list[str],
    ) -> str:
        payload = "|".join(
            [
                pair.conflict_id,
                pair.scan_id,
                action,
                winning_claim_id,
                rejected_claim_id,
                reviewer or "",
                reason or "",
                resolved_at,
                ",".join(review_event_ids),
                hashlib.sha256(pair.model_dump_json().encode("utf-8")).hexdigest(),
            ]
        )
        return f"sig:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _reviewer_signature(
        *,
        claim: MemoryClaim,
        scan_id: str,
        previous_status: str,
        new_status: str,
        reviewer: str | None,
        reason: str | None,
        reviewed_at: str,
        field_diffs: list[MemoryReviewFieldDiff],
        signal_explanations: list[MemoryReviewSignalExplanation],
    ) -> str:
        payload = "|".join(
            [
                claim.claim_id,
                scan_id,
                previous_status,
                new_status,
                reviewer or "",
                reason or "",
                reviewed_at,
                hashlib.sha256(
                    "".join(item.model_dump_json() for item in field_diffs).encode("utf-8")
                ).hexdigest(),
                hashlib.sha256(
                    "".join(item.model_dump_json() for item in signal_explanations).encode("utf-8")
                ).hexdigest(),
            ]
        )
        return f"sig:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"

    def _intake_proofs_by_promoted_path(self, team_id: str) -> dict[str, MemoryIntakeProof]:
        try:
            documents = self.intake_repository.list_documents()
        except OSError:
            return {}
        try:
            audit_records = self.audit_logger.repository.list_audit_records()
        except OSError:
            audit_records = []

        proofs: dict[str, MemoryIntakeProof] = {}
        for document in documents:
            if document.team_id != team_id:
                continue
            draft = self._intake_draft_for_document(document)
            promoted_paths = {
                value
                for value in [document.promoted_path, draft.promoted_path if draft else None]
                if value
            }
            if not promoted_paths:
                continue
            proof = self._intake_proof(
                document=document,
                draft=draft,
                audit_run_ids=self._intake_audit_run_ids(
                    document=document,
                    draft=draft,
                    audit_records=audit_records,
                ),
            )
            for promoted_path in promoted_paths:
                proofs[self._normalize_source_path(promoted_path)] = proof
        return proofs

    def _intake_draft_for_document(self, document: IntakeDocument) -> KnowledgeDraft | None:
        try:
            return self.intake_repository.get_draft(f"draft-{document.document_id}")
        except OSError:
            return None

    def _intake_proof(
        self,
        *,
        document: IntakeDocument,
        draft: KnowledgeDraft | None,
        audit_run_ids: list[str],
    ) -> MemoryIntakeProof:
        promoted_path = document.promoted_path or (draft.promoted_path if draft else "") or ""
        return MemoryIntakeProof(
            document_id=document.document_id,
            draft_id=draft.draft_id if draft else None,
            original_path=document.original_path,
            stored_path=document.stored_path,
            promoted_path=promoted_path,
            source_hash=document.source_hash,
            source_hash_verified=self._verify_intake_source_hash(document),
            review_status=draft.review_status if draft else document.status,
            intake_audit_run_ids=audit_run_ids,
            section_proofs=self._intake_section_proofs(draft),
        )

    @staticmethod
    def _intake_section_proofs(draft: KnowledgeDraft | None) -> list[MemoryIntakeSectionProof]:
        if draft is None:
            return []
        proofs: list[MemoryIntakeSectionProof] = []
        for section in draft.sections:
            proofs.append(
                MemoryIntakeSectionProof(
                    section_id=section.section_id,
                    heading=section.heading,
                    source_reference=section.source_reference,
                    start_line=section.source_span.start_line if section.source_span else None,
                    end_line=section.source_span.end_line if section.source_span else None,
                    section_hash=section.section_hash,
                )
            )
        return proofs

    @staticmethod
    def _intake_audit_run_ids(
        *,
        document: IntakeDocument,
        draft: KnowledgeDraft | None,
        audit_records: list[AuditRecord],
    ) -> list[str]:
        draft_id = draft.draft_id if draft else f"draft-{document.document_id}"
        matches = [
            record.run_id
            for record in audit_records
            if record.team_id == document.team_id
            and (document.document_id in record.run_id or draft_id in record.run_id)
        ]
        return sorted(matches)

    @classmethod
    def _verify_intake_source_hash(cls, document: IntakeDocument) -> bool | None:
        if not document.source_hash:
            return None
        for path in cls._stored_path_candidates(document.stored_path):
            if not path.exists():
                continue
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            return f"sha256:{digest}" == document.source_hash
        return None

    @staticmethod
    def _stored_path_candidates(path_value: str) -> list[Path]:
        path = Path(path_value)
        candidates = [path]
        if not path.is_absolute():
            candidates.append(PROJECT_ROOT / path)
        return candidates

    @staticmethod
    def _normalize_source_path(value: str) -> str:
        normalized = value.replace("\\", "/").strip().lower()
        project_root = PROJECT_ROOT.as_posix().lower().rstrip("/")
        if normalized.startswith(f"{project_root}/"):
            return normalized.removeprefix(f"{project_root}/")
        return normalized

    @staticmethod
    def _review_queue_markdown(scan: MemoryScanResult) -> str:
        lines = [
            f"# Memory Diff: {scan.team_id}/{scan.repo_name or '_team'}",
            "",
            f"- Scan: `{scan.scan_id}`",
            f"- Schema: `{scan.schema_version}`",
            f"- Claims: {len(scan.claims)}",
            f"- Sources: {len(scan.sources)}",
            f"- Commit: `{scan.provenance.commit_sha if scan.provenance else 'unknown'}`",
            f"- Dirty: {scan.provenance.dirty if scan.provenance else 'unknown'}",
            f"- Citation validity: {scan.validation.citation_validity:.2f}",
            f"- Unsupported claim rate: {scan.validation.unsupported_claim_rate:.2f}",
            f"- Secret leakage count: {scan.validation.secret_leakage_count}",
            "",
            "## Review Queue",
            "",
        ]
        for claim in sorted(scan.claims, key=lambda item: item.claim_id):
            lines.extend(MemoryDistillationService._claim_markdown_lines(claim))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _diff_markdown(
        *,
        scan: MemoryScanResult,
        base: MemoryScanResult,
        added: list[MemoryClaim],
        removed: list[MemoryClaim],
        changed: list[MemoryClaim],
        unchanged: int,
    ) -> str:
        lines = [
            f"# Memory Diff: {scan.team_id}/{scan.repo_name or '_team'}",
            "",
            f"- Base scan: `{base.scan_id}`",
            f"- Current scan: `{scan.scan_id}`",
            f"- Added claims: {len(added)}",
            f"- Removed claims: {len(removed)}",
            f"- Changed claims: {len(changed)}",
            f"- Unchanged claims: {unchanged}",
            "",
        ]
        for title, claims in [
            ("Added Claims", added),
            ("Removed Claims", removed),
            ("Changed Claims", changed),
        ]:
            lines.extend([f"## {title}", ""])
            if not claims:
                lines.extend(["_None._", ""])
                continue
            for claim in claims:
                lines.extend(MemoryDistillationService._claim_markdown_lines(claim))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _claim_markdown_lines(claim: MemoryClaim) -> list[str]:
        status = claim.governance.status
        marker = "+" if status in {"candidate", "approved"} else "?"
        source_paths = ", ".join(span.path for span in claim.evidence.spans[:3])
        lines = [
            (
                f"{marker} `{claim.claim_id}` `{status}` `{claim.governance.risk_level}` "
                f"{claim.entity.canonical_name} --{claim.relation.type}--> "
                f"{claim.relation.value or claim.relation.object_entity_id or '_'}"
            ),
            f"  - method: {claim.extraction.method}",
            f"  - confidence: {claim.extraction.confidence:.2f}",
            f"  - evidence: {source_paths or 'missing'}",
        ]
        if claim.evidence.intake_proofs:
            proof = claim.evidence.intake_proofs[0]
            lines.append(
                "  - intake proof: "
                f"{proof.document_id} / {proof.draft_id or '_'} / "
                f"{len(proof.section_proofs)} sections"
            )
            if proof.match_explanation:
                lines.append(f"  - match explanation: {proof.match_explanation}")
        lines.append("")
        return lines

    @staticmethod
    def _claim_compare_key(claim: MemoryClaim) -> dict[str, object]:
        payload = claim.model_dump()
        payload.pop("scan_id", None)
        payload.pop("audit", None)
        return payload

    @staticmethod
    def _test_mapping_claim(
        *,
        team_id: str,
        repo_name: str,
        scan_id: str,
        created_at: str,
        mapping: TestMapping,
        source: SourceRecord,
        span: SourceSpan,
    ) -> MemoryClaim:
        status = "approved" if mapping.confidence >= 0.95 else "candidate"
        return MemoryDistillationService._claim(
            team_id=team_id,
            repo_name=repo_name,
            scan_id=scan_id,
            created_at=created_at,
            entity_type="code_file",
            entity_name=mapping.source_file,
            relation_type="tested_by",
            object_entity_id=MemoryDistillationService._entity_id("test", mapping.test_file),
            value=mapping.test_file,
            source=source,
            span=span,
            method=STRUCTURAL_EXTRACTION,
            confidence=mapping.confidence,
            status=status,
            risk_level="low",
        )

    @classmethod
    def _doc_claims(
        cls,
        *,
        team_id: str,
        repo_name: str,
        scan_id: str,
        created_at: str,
        entry: _DocEntry,
        source: SourceRecord,
        intake_proof: MemoryIntakeProof | None = None,
    ) -> list[MemoryClaim]:
        span = source.spans[0]
        claims: list[MemoryClaim] = []
        doc_type = entry.doc_type.lower()
        status = "quarantined" if source.security_flags else "candidate"
        security = "blocked" if source.security_flags else "public_demo"
        for concept in cls._metadata_list(entry.metadata.get("concepts")):
            intake_proofs = cls._claim_intake_proofs(
                intake_proof=intake_proof,
                entry=entry,
                entity_name=concept,
                relation_type="documented_by",
                value=entry.source_path,
            )
            claims.append(
                cls._claim(
                    team_id=team_id,
                    repo_name=repo_name,
                    scan_id=scan_id,
                    created_at=created_at,
                    entity_type="concept",
                    entity_name=concept,
                    relation_type="documented_by",
                    value=entry.source_path,
                    source=source,
                    span=span,
                    method=SEMANTIC_EXTRACTION,
                    confidence=0.72,
                    status=status,
                    risk_level="low",
                    security_classification=security,
                    intake_proofs=intake_proofs,
                )
            )
        semantic_entity, relation, risk_level = cls._doc_memory_shape(doc_type, entry.source_path)
        intake_proofs = cls._claim_intake_proofs(
            intake_proof=intake_proof,
            entry=entry,
            entity_name=cls._doc_key(entry),
            relation_type=relation,
            value=entry.title,
        )
        claims.append(
            cls._claim(
                team_id=team_id,
                repo_name=repo_name,
                scan_id=scan_id,
                created_at=created_at,
                entity_type=semantic_entity,
                entity_name=cls._doc_key(entry),
                relation_type=relation,
                value=entry.title,
                condition=cls._doc_condition(entry),
                source=source,
                span=span,
                method=SEMANTIC_EXTRACTION,
                confidence=0.68,
                status=status,
                risk_level=risk_level,
                security_classification=security,
                aliases=[entry.title, entry.source_path],
                intake_proofs=intake_proofs,
            )
        )
        return claims

    @classmethod
    def _claim_intake_proofs(
        cls,
        *,
        intake_proof: MemoryIntakeProof | None,
        entry: _DocEntry,
        entity_name: str,
        relation_type: str,
        value: str | None,
    ) -> list[MemoryIntakeProof] | None:
        if intake_proof is None:
            return None
        matched_terms = cls._semantic_matched_terms(
            entry=entry,
            entity_name=entity_name,
            relation_type=relation_type,
            value=value,
        )
        explanation = cls._semantic_match_explanation(
            entry=entry,
            proof=intake_proof,
            entity_name=entity_name,
            relation_type=relation_type,
            value=value,
            matched_terms=matched_terms,
        )
        return [
            intake_proof.model_copy(
                deep=True,
                update={
                    "match_explanation": explanation,
                    "matched_terms": matched_terms,
                },
            )
        ]

    @classmethod
    def _semantic_matched_terms(
        cls,
        *,
        entry: _DocEntry,
        entity_name: str,
        relation_type: str,
        value: str | None,
    ) -> list[str]:
        value_text = "" if value and ("/" in value or "\\" in value) else value or ""
        claim_terms = cls._tokens(" ".join([entity_name, relation_type, value_text]))
        evidence_terms = cls._tokens(
            " ".join(
                [
                    entry.title,
                    entry.doc_type,
                    entry.source_path,
                    " ".join(cls._metadata_list(entry.metadata.get("concepts"))),
                    entry.content,
                ]
            )
        )
        return sorted((claim_terms & evidence_terms) - MATCH_STOP_WORDS)[:12]

    @staticmethod
    def _semantic_match_explanation(
        *,
        entry: _DocEntry,
        proof: MemoryIntakeProof,
        entity_name: str,
        relation_type: str,
        value: str | None,
        matched_terms: list[str],
    ) -> str:
        terms = ", ".join(matched_terms) if matched_terms else "metadata/path evidence"
        hash_state = (
            "source hash verified"
            if proof.source_hash_verified is True
            else "source hash not verified"
        )
        return (
            f"Matched claim '{entity_name}' ({relation_type} -> {value or '_'}) to "
            f"{entry.doc_type} document '{entry.title}' because deterministic terms "
            f"[{terms}] appear in the promoted structured document. Raw trace covers "
            f"{len(proof.section_proofs)} parsed sections and {hash_state}."
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {match.group(0).lower() for match in TOKEN_RE.finditer(value)}

    @staticmethod
    def _doc_memory_shape(doc_type: str, source_path: str) -> tuple[str, str, str]:
        lowered = source_path.lower()
        if doc_type == "incident" or "/docs/incidents/" in lowered:
            return "incident", "risk_for", "medium"
        if doc_type == "runbook" or "/docs/runbooks/" in lowered:
            return "runbook", "mitigates", "high"
        if doc_type == "historical-pr" or "/docs/historical-pr/" in lowered:
            return "pr", "changed_by", "medium"
        if doc_type == "historical-jira" or "/docs/historical-jira/" in lowered:
            return "ticket", "documented_by", "medium"
        if doc_type == "architecture" or "/docs/architecture/" in lowered:
            return "decision", "documented_by", "medium"
        return "concept", "documented_by", "low"

    @staticmethod
    def _doc_condition(entry: _DocEntry) -> str | None:
        component = entry.metadata.get("component")
        app = entry.metadata.get("app")
        values = [str(item) for item in [app, component] if item]
        return " / ".join(values) if values else None

    @staticmethod
    def _doc_key(entry: _DocEntry) -> str:
        stem = Path(entry.source_path).stem
        return stem or entry.title

    @classmethod
    def _claim(
        cls,
        *,
        team_id: str,
        repo_name: str,
        scan_id: str,
        created_at: str,
        entity_type: str,
        entity_name: str,
        relation_type: str,
        source: SourceRecord,
        span: SourceSpan,
        method: str,
        confidence: float,
        status: str,
        risk_level: str,
        value: str | None = None,
        object_entity_id: str | None = None,
        condition: str | None = None,
        aliases: list[str] | None = None,
        security_classification: str = "public_demo",
        intake_proofs: list[MemoryIntakeProof] | None = None,
    ) -> MemoryClaim:
        entity = MemoryEntity(
            entity_id=cls._entity_id(entity_type, entity_name),
            entity_type=entity_type,
            canonical_name=entity_name,
            aliases=sorted({*(aliases or []), entity_name}),
        )
        evidence_span = MemoryEvidenceSpan(
            source_id=source.source_id,
            source_type=source.source_type,
            path=source.path,
            commit_sha=source.commit_sha,
            start_line=span.start_line,
            end_line=span.end_line,
            excerpt_hash=span.text_hash,
            span_id=span.span_id,
        )
        claim_key = "|".join(
            [
                team_id,
                repo_name,
                entity.entity_id,
                relation_type,
                object_entity_id or "",
                value or "",
                condition or "",
                span.span_id,
            ]
        )
        return MemoryClaim(
            claim_id=f"claim:{cls._stable_id(claim_key)}",
            team_id=team_id,
            repo_id=repo_name,
            scan_id=scan_id,
            entity=entity,
            relation=MemoryRelation(
                type=relation_type,
                object_entity_id=object_entity_id,
                value=value,
                condition=condition,
            ),
            evidence=MemoryEvidence(
                source_ids=[source.source_id],
                spans=[evidence_span],
                intake_proofs=intake_proofs or [],
            ),
            extraction=ExtractionInfo(
                method=method,
                extractor_version=EXTRACTOR_VERSION,
                confidence=confidence,
            ),
            governance=GovernanceInfo(status=status, risk_level=risk_level),
            security=SecurityInfo(
                classification=security_classification,
                redaction_applied=bool(source.security_flags),
            ),
            audit=ClaimAuditInfo(created_at=created_at, updated_at=created_at),
        )

    @classmethod
    def _source_record(
        cls,
        *,
        team_id: str,
        repo_name: str | None,
        source_type: str,
        path: str,
        content: str,
        indexed_at: str,
        trust_level: str,
        commit_sha: str | None,
    ) -> SourceRecord:
        content_hash = cls._sha256(content)
        source_key = f"{team_id}:{repo_name}:{source_type}:{path}:{content_hash}"
        source_id = f"src:{cls._stable_id(source_key)}"
        lines = content.splitlines()
        end_line = len(lines) if lines else 1
        span = cls._source_span(
            source_id=source_id,
            content=content,
            start_line=1,
            end_line=end_line,
        )
        return SourceRecord(
            source_id=source_id,
            source_type=source_type,
            team_id=team_id,
            repo_name=repo_name,
            path=path,
            commit_sha=commit_sha,
            content_hash=content_hash,
            indexed_at=indexed_at,
            trust_level=trust_level,
            security_flags=cls._security_flags(content),
            spans=[span],
        )

    @classmethod
    def _span_for_symbol(
        cls,
        source: SourceRecord,
        content: str,
        symbol: SymbolNode,
    ) -> SourceSpan:
        if symbol.start_line is None:
            return source.spans[0]
        span = cls._source_span(
            source_id=source.source_id,
            content=content,
            start_line=symbol.start_line,
            end_line=symbol.end_line or symbol.start_line,
        )
        if span.span_id not in {item.span_id for item in source.spans}:
            source.spans.append(span)
        return span

    @classmethod
    def _source_span(
        cls,
        *,
        source_id: str,
        content: str,
        start_line: int,
        end_line: int,
    ) -> SourceSpan:
        lines = content.splitlines()
        start_index = max(start_line - 1, 0)
        end_index = min(end_line, len(lines)) if lines else 0
        excerpt = "\n".join(lines[start_index:end_index]) if lines else content
        text_hash = cls._sha256(excerpt)
        span_id = f"span:{cls._stable_id(f'{source_id}:{start_line}:{end_line}:{text_hash}')}"
        return SourceSpan(
            span_id=span_id,
            source_id=source_id,
            start_line=start_line,
            end_line=end_line,
            text_hash=text_hash,
            preview=cls._redact_preview(" ".join(excerpt.split()))[:240],
        )

    @classmethod
    def _validate(
        cls,
        *,
        sources: list[SourceRecord],
        claims: list[MemoryClaim],
    ) -> MemoryValidationSummary:
        source_by_id = {source.source_id: source for source in sources}
        valid_evidence_count = 0
        total_evidence_count = 0
        unsupported_claims = 0
        for claim in claims:
            if not claim.evidence.spans:
                unsupported_claims += 1
                continue
            claim_supported = True
            for span in claim.evidence.spans:
                total_evidence_count += 1
                source = source_by_id.get(span.source_id)
                valid_span_ids = {item.span_id for item in source.spans} if source else set()
                if span.span_id in valid_span_ids:
                    valid_evidence_count += 1
                else:
                    claim_supported = False
            if not claim_supported:
                unsupported_claims += 1
        citation_validity = (
            valid_evidence_count / total_evidence_count if total_evidence_count else 1.0
        )
        semantic_candidates = [
            claim for claim in claims if claim.extraction.method == SEMANTIC_EXTRACTION
        ]
        auto_promoted_semantic = [
            claim for claim in semantic_candidates if claim.governance.status == "approved"
        ]
        leaked_secret_claims = [
            claim
            for claim in claims
            if claim.security.classification == "blocked"
            and claim.governance.status != "quarantined"
        ]
        warnings = []
        if auto_promoted_semantic:
            warnings.append("Semantic claims were auto-promoted; MVP policy expects review first.")
        if leaked_secret_claims:
            warnings.append("Sensitive sources produced non-quarantined claims.")
        return MemoryValidationSummary(
            citation_validity=citation_validity,
            unsupported_claim_rate=unsupported_claims / len(claims) if claims else 0.0,
            secret_leakage_count=len(leaked_secret_claims),
            structural_claims=len(
                [claim for claim in claims if claim.extraction.method == STRUCTURAL_EXTRACTION]
            ),
            semantic_candidate_claims=len(semantic_candidates),
            auto_promoted_semantic_claims=len(auto_promoted_semantic),
            warnings=warnings,
        )

    @staticmethod
    def _dedupe_claims(claims: list[MemoryClaim]) -> list[MemoryClaim]:
        deduped: dict[str, MemoryClaim] = {}
        for claim in claims:
            deduped.setdefault(claim.claim_id, claim)
        return sorted(deduped.values(), key=lambda item: item.claim_id)

    def _load_doc_entries(self, team_id: str) -> list[_DocEntry]:
        pack = self.pack_loader.load(team_id)
        pack_dir = (self.pack_loader.packs_dir / pack.team_id).resolve()
        entries: list[_DocEntry] = []
        for relative_dir in pack.document_paths:
            doc_dir = (pack_dir / relative_dir).resolve()
            if not doc_dir.is_relative_to(pack_dir):
                raise PathTraversalError(
                    f"Knowledge document path escapes pack directory: {relative_dir}"
                )
            if not doc_dir.exists():
                continue
            for path in sorted(doc_dir.rglob("*.md")):
                raw = self._read_text(path)
                metadata, content = self._split_front_matter(raw)
                title = str(metadata.get("title") or self._extract_title(content) or path.stem)
                doc_type = str(metadata.get("doc_type") or self._infer_doc_type(path, pack_dir))
                entries.append(
                    _DocEntry(
                        path=path,
                        source_path=display_path(path),
                        metadata={**metadata, "team_id": team_id},
                        content=content,
                        title=title,
                        doc_type=doc_type,
                    )
                )
        return entries

    @staticmethod
    def _split_front_matter(raw: str) -> tuple[dict[str, Any], str]:
        candidate = raw.lstrip()
        while candidate.startswith("<!--"):
            end_index = candidate.find("-->")
            if end_index == -1:
                return {}, candidate
            candidate = candidate[end_index + 3 :].lstrip()
        if not candidate.startswith("---\n"):
            return {}, candidate
        parts = candidate.split("---\n", 2)
        if len(parts) != 3:
            return {}, candidate
        metadata = yaml.safe_load(parts[1]) or {}
        return metadata if isinstance(metadata, dict) else {}, parts[2]

    @staticmethod
    def _extract_title(content: str) -> str | None:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return None

    @staticmethod
    def _infer_doc_type(path: Path, pack_dir: Path) -> str:
        try:
            return path.relative_to(pack_dir / "docs").parts[0]
        except (ValueError, IndexError):
            return path.parent.name

    @staticmethod
    def _metadata_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)] if str(value).strip() else []

    @staticmethod
    def _file_source_type(role: str) -> str:
        return "test" if role == "test" else "code"

    @staticmethod
    def _doc_source_type(entry: _DocEntry) -> str:
        normalized = entry.doc_type.lower()
        if normalized in {"runbook", "incident", "test", "workflow"}:
            return normalized
        if normalized == "historical-pr":
            return "pr"
        if normalized == "historical-jira":
            return "ticket"
        return "doc"

    @staticmethod
    def _doc_trust_level(entry: _DocEntry) -> str:
        normalized = entry.doc_type.lower()
        return "high" if normalized in {"incident", "runbook", "architecture"} else "medium"

    @classmethod
    def _missing_source(
        cls,
        team_id: str,
        repo_name: str,
        path: str,
        indexed_at: str,
        commit_sha: str | None,
    ) -> tuple[SourceRecord, str]:
        source = cls._source_record(
            team_id=team_id,
            repo_name=repo_name,
            source_type="code",
            path=path,
            content="",
            indexed_at=indexed_at,
            trust_level="low",
            commit_sha=commit_sha,
        )
        return source, ""

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""

    @staticmethod
    def _security_flags(content: str) -> list[str]:
        flags = []
        if SECRET_RE.search(content):
            flags.append("secret_like_assignment")
        if AWS_ACCESS_KEY_RE.search(content):
            flags.append("aws_access_key")
        if JWT_RE.search(content):
            flags.append("jwt_like_token")
        if PEM_PRIVATE_KEY_RE.search(content):
            flags.append("pem_private_key")
        return sorted(flags)

    @staticmethod
    def _redact_preview(value: str) -> str:
        redacted = SECRET_VALUE_RE.sub(
            lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
            value,
        )
        redacted = AWS_ACCESS_KEY_RE.sub("[REDACTED_AWS_ACCESS_KEY]", redacted)
        redacted = JWT_RE.sub("[REDACTED_JWT]", redacted)
        return PEM_PRIVATE_KEY_RE.sub("-----BEGIN [REDACTED PRIVATE KEY]-----", redacted)

    @classmethod
    def _repo_provenance(cls, root: Path) -> RepoProvenanceInfo:
        git_root = cls._git_output(root, "rev-parse", "--show-toplevel")
        commit_sha = cls._git_output(root, "rev-parse", "HEAD") if git_root else None
        dirty_lines = (
            cls._git_output(root, "status", "--porcelain", "--untracked-files=normal", "--", ".")
            if git_root
            else ""
        )
        dirty_paths = [
            line[3:].strip()
            for line in dirty_lines.splitlines()
            if len(line) > 3 and line[3:].strip()
        ]
        return RepoProvenanceInfo(
            repo_path=display_path(root),
            git_root=display_path(git_root) if git_root else None,
            commit_sha=commit_sha,
            dirty=bool(dirty_paths),
            dirty_paths=dirty_paths[:50],
            scanner_version=EXTRACTOR_VERSION,
        )

    @staticmethod
    def _git_output(root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    @classmethod
    def _entity_id(cls, entity_type: str, name: str) -> str:
        return f"{entity_type}:{cls._stable_id(f'{entity_type}:{name}')}"

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _relation_compare_value(claim: MemoryClaim) -> str:
    return "|".join(
        [
            claim.relation.object_entity_id or "",
            claim.relation.value or "",
            claim.relation.condition or "",
        ]
    )
