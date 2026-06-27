# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from dream.audit.logger import AuditLogger
from dream.codebase import CodebaseIndexer, CodebaseIndexRepository
from dream.codebase.models import SymbolNode, TestMapping
from dream.core.errors import DreamError, PathTraversalError
from dream.core.paths import display_path, resolve_project_path
from dream.knowledge import KnowledgePackLoader
from dream.memory.models import (
    ClaimAuditInfo,
    ExtractionInfo,
    GovernanceInfo,
    MemoryClaim,
    MemoryEntity,
    MemoryEvidence,
    MemoryEvidenceSpan,
    MemoryRelation,
    MemoryScanResult,
    MemoryValidationSummary,
    SecurityInfo,
    SourceRecord,
    SourceSpan,
)
from dream.memory.repository import MemoryDistillationRepository

STRUCTURAL_EXTRACTION = "deterministic_structure"
SEMANTIC_EXTRACTION = "heuristic_semantic"
EXTRACTOR_VERSION = "memory-distillation-v0"
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|private[_-]?key)\s*[:=]"
)


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
        pack_loader: KnowledgePackLoader | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.repository = repository or MemoryDistillationRepository()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository(
            self.repository.artifacts_dir
        )
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.audit_logger = audit_logger or AuditLogger()

    def scan(
        self,
        *,
        team_id: str,
        repo_path: str | Path,
        repo_name: str | None = None,
    ) -> MemoryScanResult:
        created_at = datetime.now(UTC).isoformat()
        scan_id = f"memscan-{uuid4().hex[:12]}"
        root = resolve_project_path(repo_path, must_exist=True)
        index = CodebaseIndexer(
            repository=self.codebase_repository,
            audit_logger=self.audit_logger,
        ).index(team_id=team_id, repo_path=root, repo_name=repo_name)

        sources: list[SourceRecord] = []
        claims: list[MemoryClaim] = []
        warnings: list[str] = []
        source_by_path: dict[str, tuple[SourceRecord, str]] = {}

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
            doc_source = self._source_record(
                team_id=team_id,
                repo_name=index.repo_name,
                source_type=self._doc_source_type(entry),
                path=entry.source_path,
                content=entry.content,
                indexed_at=created_at,
                trust_level=self._doc_trust_level(entry),
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
                )
            )

        claims = self._dedupe_claims(claims)
        validation = self._validate(sources=sources, claims=claims)
        scan = MemoryScanResult(
            scan_id=scan_id,
            team_id=team_id,
            repo_name=index.repo_name,
            created_at=created_at,
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

    def diff_markdown(self, *, team_id: str, scan_id: str = "latest") -> str:
        scan = self.repository.load_scan(team_id, scan_id)
        lines = [
            f"# Memory Diff: {scan.team_id}/{scan.repo_name or '_team'}",
            "",
            f"- Scan: `{scan.scan_id}`",
            f"- Claims: {len(scan.claims)}",
            f"- Sources: {len(scan.sources)}",
            f"- Citation validity: {scan.validation.citation_validity:.2f}",
            f"- Unsupported claim rate: {scan.validation.unsupported_claim_rate:.2f}",
            f"- Secret leakage count: {scan.validation.secret_leakage_count}",
            "",
            "## Review Queue",
            "",
        ]
        for claim in sorted(scan.claims, key=lambda item: item.claim_id):
            status = claim.governance.status
            marker = "+" if status in {"candidate", "approved"} else "?"
            source_paths = ", ".join(span.path for span in claim.evidence.spans[:3])
            lines.extend(
                [
                    (
                        f"{marker} `{status}` `{claim.governance.risk_level}` "
                        f"{claim.entity.canonical_name} --{claim.relation.type}--> "
                        f"{claim.relation.value or claim.relation.object_entity_id or '_'}"
                    ),
                    f"  - method: {claim.extraction.method}",
                    f"  - confidence: {claim.extraction.confidence:.2f}",
                    f"  - evidence: {source_paths or 'missing'}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

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
    ) -> list[MemoryClaim]:
        span = source.spans[0]
        claims: list[MemoryClaim] = []
        doc_type = entry.doc_type.lower()
        status = "quarantined" if source.security_flags else "candidate"
        security = "blocked" if source.security_flags else "public_demo"
        for concept in cls._metadata_list(entry.metadata.get("concepts")):
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
                )
            )
        semantic_entity, relation, risk_level = cls._doc_memory_shape(doc_type, entry.source_path)
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
            )
        )
        return claims

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
            evidence=MemoryEvidence(source_ids=[source.source_id], spans=[evidence_span]),
            extraction=ExtractionInfo(
                method=method,
                extractor_version=EXTRACTOR_VERSION,
                confidence=confidence,
            ),
            governance=GovernanceInfo(status=status, risk_level=risk_level),
            security=SecurityInfo(classification=security_classification),
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
            preview=" ".join(excerpt.split())[:240],
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
    ) -> tuple[SourceRecord, str]:
        source = cls._source_record(
            team_id=team_id,
            repo_name=repo_name,
            source_type="code",
            path=path,
            content="",
            indexed_at=indexed_at,
            trust_level="low",
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
        return ["secret_like_token"] if SECRET_RE.search(content) else []

    @classmethod
    def _entity_id(cls, entity_type: str, name: str) -> str:
        return f"{entity_type}:{cls._stable_id(f'{entity_type}:{name}')}"

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
