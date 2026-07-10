# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from dream.audit.logger import AuditLogger
from dream.codebase.models import FileNode, RepoIndex, SymbolNode
from dream.codebase.repository import CodebaseIndexRepository
from dream.core.errors import PathTraversalError
from dream.core.paths import display_path
from dream.graph.models import EvidenceEdge, EvidenceGraph, EvidenceNode
from dream.graph.repository import EvidenceGraphRepository
from dream.knowledge import KnowledgePackLoader
from dream.security.models import ResourceAccess


@dataclass(frozen=True)
class _DocEntry:
    path: Path
    source_path: str
    metadata: dict[str, Any]
    title: str
    content: str
    doc_type: str
    node_id: str


class EvidenceGraphBuilder:
    def __init__(
        self,
        *,
        pack_loader: KnowledgePackLoader | None = None,
        codebase_repository: CodebaseIndexRepository | None = None,
        repository: EvidenceGraphRepository | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.codebase_repository = codebase_repository or CodebaseIndexRepository()
        self.repository = repository or EvidenceGraphRepository()
        self.audit_logger = audit_logger or AuditLogger()

    def build(self, *, team_id: str, repo_name: str | None = None) -> EvidenceGraph:
        pack = self.pack_loader.load(team_id)
        pack_dir = self.pack_loader.packs_dir / pack.team_id
        repo_index = self.codebase_repository.try_load(team_id, repo_name) if repo_name else None
        warnings = []
        if repo_name and repo_index is None:
            warnings.append(
                "No codebase index found; evidence graph includes knowledge documents only."
            )

        nodes: dict[str, EvidenceNode] = {}
        aliases: dict[str, str] = {}
        edge_keys: set[tuple[str, str, str]] = set()
        edges: list[EvidenceEdge] = []

        def add_node(node: EvidenceNode) -> EvidenceNode:
            existing = nodes.get(node.node_id)
            if existing is not None:
                merged_aliases = sorted(set(existing.aliases) | set(node.aliases))
                merged_concepts = sorted(set(existing.concepts) | set(node.concepts))
                merged_metadata = {**existing.metadata, **node.metadata}
                nodes[node.node_id] = existing.model_copy(
                    update={
                        "aliases": merged_aliases,
                        "concepts": merged_concepts,
                        "metadata": merged_metadata,
                        "source_path": existing.source_path or node.source_path,
                        "access": existing.access.restrictive_merge(node.access),
                    }
                )
                node = nodes[node.node_id]
            else:
                nodes[node.node_id] = node
            for alias in self._node_aliases(node):
                aliases.setdefault(self._normalize_alias(alias), node.node_id)
            return node

        def add_edge(
            from_node_id: str,
            to_node_id: str,
            edge_type: str,
            confidence: float,
            reason: str,
        ) -> None:
            if from_node_id == to_node_id:
                return
            key = (from_node_id, to_node_id, edge_type)
            if key in edge_keys:
                return
            edge_keys.add(key)
            edges.append(
                EvidenceEdge(
                    edge_id=self._stable_id(":".join(key)),
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    edge_type=edge_type,
                    confidence=confidence,
                    reason=reason,
                )
            )

        doc_entries = self._load_doc_entries(pack_dir, pack.document_paths, team_id)
        for entry in doc_entries:
            doc_node = add_node(
                EvidenceNode(
                    node_id=entry.node_id,
                    node_type=self._doc_node_type(entry.doc_type, entry.source_path),
                    key=self._doc_key(entry),
                    title=entry.title,
                    source_path=entry.source_path,
                    aliases=self._doc_aliases(entry),
                    concepts=self._metadata_list(entry.metadata.get("concepts")),
                    metadata={
                        "doc_type": entry.doc_type,
                        "app": str(entry.metadata.get("app", "")),
                        "component": str(entry.metadata.get("component", "")),
                    },
                    access=ResourceAccess.from_metadata(entry.metadata),
                )
            )
            for concept in doc_node.concepts:
                concept_node = add_node(
                    self._concept_node(team_id, concept, access=doc_node.access)
                )
                add_edge(
                    concept_node.node_id,
                    doc_node.node_id,
                    "MENTIONED_IN",
                    0.85,
                    "Document front matter lists this concept.",
                )

        if repo_index is not None:
            self._add_codebase_nodes(repo_index, add_node, add_edge)

        for entry in doc_entries:
            doc_node_id = entry.node_id
            for code_path in self._metadata_list(entry.metadata.get("related_code")):
                code_node = self._resolve_or_stub_code_node(
                    team_id=team_id,
                    code_path=code_path,
                    aliases=aliases,
                    nodes=nodes,
                    add_node=add_node,
                    access=ResourceAccess.from_metadata(entry.metadata),
                )
                add_edge(
                    doc_node_id,
                    code_node.node_id,
                    "AFFECTS",
                    0.8,
                    "Document front matter links this code file.",
                )
                for concept in self._metadata_list(entry.metadata.get("concepts")):
                    concept_node = add_node(
                        self._concept_node(
                            team_id,
                            concept,
                            access=ResourceAccess.from_metadata(entry.metadata),
                        )
                    )
                    add_edge(
                        concept_node.node_id,
                        code_node.node_id,
                        "IMPLEMENTED_BY",
                        0.72,
                        "Concept is linked to a related code file by document metadata.",
                    )
            self._add_related_metadata_edges(entry, aliases, add_edge)

        graph = EvidenceGraph(
            graph_id=self._stable_id(f"{team_id}:{repo_name or '_team'}:{datetime.now(UTC)}"),
            team_id=team_id,
            repo_name=repo_name,
            built_at=datetime.now(UTC).isoformat(),
            nodes=sorted(nodes.values(), key=lambda item: (item.node_type, item.title)),
            edges=sorted(
                edges,
                key=lambda item: (item.from_node_id, item.edge_type, item.to_node_id),
            ),
            summary=(
                f"Evidence graph for {team_id}/{repo_name or '_team'} contains "
                f"{len(nodes)} nodes and {len(edges)} edges."
            ),
            warnings=warnings,
        )
        output_path = self.repository.save(graph)
        self.audit_logger.log_generation(
            run_id=f"evidence-graph-{self._stable_id(graph.graph_id)[:12]}",
            use_case="evidence_graph_build",
            team_id=team_id,
            repo_name=repo_name,
            input_payload={"team_id": team_id, "repo_name": repo_name},
            retrieved_source_paths=[node.source_path for node in graph.nodes if node.source_path],
            model_provider="deterministic",
            model_name="evidence-graph-lite-v1",
            output_path=display_path(output_path),
            status="success",
            warnings=warnings,
        )
        return graph

    def _add_codebase_nodes(
        self,
        repo_index: RepoIndex,
        add_node,
        add_edge,
    ) -> None:
        files_by_path = {item.path: item for item in repo_index.files}
        for file_node in repo_index.files:
            add_node(self._file_node(repo_index.team_id, file_node))
        for symbol in repo_index.symbols:
            symbol_node = add_node(self._symbol_node(repo_index.team_id, symbol))
            file_node = add_node(
                self._file_stub_node(
                    team_id=repo_index.team_id,
                    path=symbol.file_path,
                    node_type="test_file" if "/test/" in symbol.file_path.lower() else "code_file",
                    access=symbol.access,
                )
            )
            add_edge(
                symbol_node.node_id,
                file_node.node_id,
                "DEFINED_IN",
                0.95,
                "Symbol extractor mapped the symbol to this file.",
            )
            for concept in symbol.concepts:
                concept_node = add_node(
                    self._concept_node(repo_index.team_id, concept, access=symbol.access)
                )
                add_edge(
                    concept_node.node_id,
                    symbol_node.node_id,
                    "IMPLEMENTED_BY",
                    0.7,
                    "Symbol concepts were derived from codebase memory.",
                )
        for mapping in repo_index.tests:
            source_node = add_node(
                self._file_stub_node(
                    repo_index.team_id,
                    mapping.source_file,
                    "code_file",
                    access=self._path_access(
                        files_by_path,
                        mapping.source_file,
                        fallback=repo_index.access,
                    ),
                )
            )
            test_node = add_node(
                self._file_stub_node(
                    repo_index.team_id,
                    mapping.test_file,
                    "test_file",
                    access=self._path_access(
                        files_by_path,
                        mapping.test_file,
                        fallback=repo_index.access,
                    ),
                )
            )
            add_edge(
                source_node.node_id,
                test_node.node_id,
                "TESTED_BY",
                mapping.confidence,
                mapping.reason,
            )
        for mapping in repo_index.concepts:
            concept_node = add_node(
                self._concept_node(
                    repo_index.team_id,
                    mapping.concept,
                    access=mapping.access,
                )
            )
            for file_path in mapping.related_files:
                file_node = add_node(
                    self._file_stub_node(
                        repo_index.team_id,
                        file_path,
                        "code_file",
                        access=self._path_access(
                            files_by_path,
                            file_path,
                            fallback=repo_index.access,
                        ),
                    )
                )
                add_edge(
                    concept_node.node_id,
                    file_node.node_id,
                    "IMPLEMENTED_BY",
                    mapping.confidence,
                    mapping.reason,
                )
            for test_path in mapping.related_tests:
                test_node = add_node(
                    self._file_stub_node(
                        repo_index.team_id,
                        test_path,
                        "test_file",
                        access=self._path_access(
                            files_by_path,
                            test_path,
                            fallback=repo_index.access,
                        ),
                    )
                )
                add_edge(
                    concept_node.node_id,
                    test_node.node_id,
                    "TESTED_BY",
                    mapping.confidence,
                    "Codebase memory mapped this concept to a test file.",
                )

    def _add_related_metadata_edges(
        self,
        entry: _DocEntry,
        aliases: dict[str, str],
        add_edge,
    ) -> None:
        relation_specs = [
            ("related_docs", "RELATED_TO", 0.7),
            ("related_jira", "REQUIRED_BY", 0.82),
            ("related_pr", "CHANGED_BY", 0.82),
            ("related_incidents", "REGRESSED_BY", 0.82),
        ]
        for field, edge_type, confidence in relation_specs:
            for value in self._metadata_list(entry.metadata.get(field)):
                target_node_id = self._resolve_alias(value, aliases)
                if target_node_id is None:
                    continue
                add_edge(
                    entry.node_id,
                    target_node_id,
                    edge_type,
                    confidence,
                    f"Document front matter links {field}={value}.",
                )
                for concept in self._metadata_list(entry.metadata.get("concepts")):
                    concept_node_id = self._resolve_alias(concept, aliases)
                    if concept_node_id is not None:
                        add_edge(
                            concept_node_id,
                            target_node_id,
                            edge_type,
                            confidence - 0.05,
                            f"Concept inherited {field}={value} from document metadata.",
                        )

    def _resolve_or_stub_code_node(
        self,
        *,
        team_id: str,
        code_path: str,
        aliases: dict[str, str],
        nodes: dict[str, EvidenceNode],
        add_node,
        access: ResourceAccess,
    ) -> EvidenceNode:
        resolved_id = self._resolve_alias(code_path, aliases)
        if resolved_id is not None:
            return nodes[resolved_id]
        node_type = "test_file" if self._looks_like_test_path(code_path) else "code_file"
        return add_node(self._file_stub_node(team_id, code_path, node_type, access=access))

    def _load_doc_entries(
        self,
        pack_dir: Path,
        document_paths: list[str],
        team_id: str,
    ) -> list[_DocEntry]:
        entries: list[_DocEntry] = []
        for relative_doc_dir in document_paths:
            doc_dir = self._resolve_document_dir(pack_dir, relative_doc_dir)
            if not doc_dir.exists():
                continue
            for path in sorted(doc_dir.rglob("*.md")):
                raw = path.read_text(encoding="utf-8")
                metadata, content = self._split_front_matter(raw)
                title = str(metadata.get("title") or self._extract_title(content) or path.stem)
                doc_type = str(metadata.get("doc_type") or self._infer_doc_type(path, pack_dir))
                source_path = display_path(path)
                entries.append(
                    _DocEntry(
                        path=path,
                        source_path=source_path,
                        metadata={**metadata, "team_id": team_id},
                        title=title,
                        content=content,
                        doc_type=doc_type,
                        node_id=self._node_id(
                            self._doc_node_type(doc_type, source_path),
                            source_path,
                        ),
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
    def _doc_node_type(doc_type: str, source_path: str) -> str:
        normalized = doc_type.lower()
        if normalized == "incident" or "/docs/incidents/" in source_path:
            return "incident"
        if normalized == "historical-jira" or "/docs/historical-jira/" in source_path:
            return "historical_jira"
        if normalized == "historical-pr" or "/docs/historical-pr/" in source_path:
            return "historical_pr"
        if normalized == "concept" or "/docs/concepts/" in source_path:
            return "concept_memory"
        if normalized == "testing" or "/docs/testing/" in source_path:
            return "testing_doc"
        if normalized == "runbook" or "/docs/runbooks/" in source_path:
            return "runbook"
        if normalized == "architecture" or "/docs/architecture/" in source_path:
            return "architecture_doc"
        if normalized == "domain" or "/docs/domain/" in source_path:
            return "domain_doc"
        return "knowledge_doc"

    @classmethod
    def _doc_key(cls, entry: _DocEntry) -> str:
        identifier = cls._identifier_from_path(entry.source_path)
        return identifier or entry.source_path

    @classmethod
    def _doc_aliases(cls, entry: _DocEntry) -> list[str]:
        path = Path(entry.source_path)
        aliases = [
            entry.title,
            entry.source_path,
            path.name,
            path.stem,
            cls._doc_key(entry),
        ]
        return sorted({alias for alias in aliases if alias})

    @classmethod
    def _identifier_from_path(cls, source_path: str) -> str | None:
        stem = Path(source_path).stem
        match = re.match(r"^(INC-\d{3}|DFP-\d{3}|PR-\d{3})", stem, flags=re.IGNORECASE)
        return match.group(1).upper() if match else None

    @classmethod
    def _file_node(cls, team_id: str, file_node: FileNode) -> EvidenceNode:
        node_type = "test_file" if file_node.role == "test" else "code_file"
        return EvidenceNode(
            node_id=cls._node_id(node_type, file_node.path),
            node_type=node_type,
            key=file_node.path,
            title=file_node.path,
            source_path=file_node.path,
            aliases=cls._path_aliases(file_node.path),
            concepts=file_node.concepts,
            metadata={
                "team_id": team_id,
                "language": file_node.language,
                "role": file_node.role,
                "summary": file_node.summary or "",
            },
            access=file_node.access.model_copy(deep=True),
        )

    @staticmethod
    def _path_access(
        files_by_path: dict[str, FileNode],
        path: str,
        *,
        fallback: ResourceAccess,
    ) -> ResourceAccess:
        file_node = files_by_path.get(path)
        return (file_node.access if file_node else fallback).model_copy(deep=True)

    @classmethod
    def _file_stub_node(
        cls,
        team_id: str,
        path: str,
        node_type: str,
        *,
        access: ResourceAccess | None = None,
    ) -> EvidenceNode:
        return EvidenceNode(
            node_id=cls._node_id(node_type, path),
            node_type=node_type,
            key=path,
            title=path,
            source_path=path,
            aliases=cls._path_aliases(path),
            concepts=cls._concepts_from_path(path),
            metadata={"team_id": team_id},
            access=(access or ResourceAccess()).model_copy(deep=True),
        )

    @classmethod
    def _symbol_node(cls, team_id: str, symbol: SymbolNode) -> EvidenceNode:
        key = f"{symbol.file_path}#{symbol.name}"
        return EvidenceNode(
            node_id=cls._node_id("code_symbol", key),
            node_type="code_symbol",
            key=key,
            title=f"{symbol.name} ({symbol.kind})",
            source_path=symbol.file_path,
            aliases=sorted({symbol.name, key, symbol.signature or ""} - {""}),
            concepts=symbol.concepts,
            metadata={
                "team_id": team_id,
                "kind": symbol.kind,
                "signature": symbol.signature or "",
                "summary": symbol.summary or "",
            },
            access=symbol.access.model_copy(deep=True),
        )

    @classmethod
    def _concept_node(
        cls,
        team_id: str,
        concept: str,
        *,
        access: ResourceAccess | None = None,
    ) -> EvidenceNode:
        normalized = cls._normalize_concept(concept)
        return EvidenceNode(
            node_id=cls._node_id("concept", normalized),
            node_type="concept",
            key=normalized,
            title=concept,
            aliases=[concept, normalized],
            concepts=[normalized],
            metadata={"team_id": team_id},
            access=(access or ResourceAccess()).model_copy(deep=True),
        )

    @staticmethod
    def _concepts_from_path(path: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9]+", path.replace("_", " ").replace("-", " "))
        concepts = {token.lower() for token in tokens if len(token) > 3}
        joined = " ".join(token.lower() for token in tokens)
        if "status" in joined:
            concepts.add("execution status")
        if "output" in joined and "collector" in joined:
            concepts.add("output collection")
        return sorted(concepts)

    @staticmethod
    def _path_aliases(path: str) -> list[str]:
        path_obj = Path(path)
        return sorted({path, path_obj.name, path_obj.stem})

    @staticmethod
    def _looks_like_test_path(path: str) -> bool:
        lowered = path.lower()
        return "/test/" in lowered or lowered.startswith("tests/") or lowered.endswith("test.java")

    @staticmethod
    def _node_aliases(node: EvidenceNode) -> list[str]:
        values = [node.key, node.title, node.source_path or ""]
        values.extend(node.aliases)
        if node.node_type == "concept":
            values.extend(node.concepts)
        return values

    @staticmethod
    def _resolve_alias(value: str, aliases: dict[str, str]) -> str | None:
        normalized = EvidenceGraphBuilder._normalize_alias(value)
        if normalized in aliases:
            return aliases[normalized]
        base = EvidenceGraphBuilder._normalize_alias(Path(value).name)
        return aliases.get(base)

    @staticmethod
    def _metadata_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)] if str(value).strip() else []

    @staticmethod
    def _normalize_alias(value: str) -> str:
        return value.strip().lower().replace("\\", "/")

    @staticmethod
    def _normalize_concept(value: str) -> str:
        return " ".join(value.lower().replace("-", " ").replace("_", " ").split())

    @classmethod
    def _node_id(cls, node_type: str, key: str) -> str:
        return f"{node_type}:{cls._stable_id(f'{node_type}:{key}')}"

    @staticmethod
    def _resolve_document_dir(pack_dir: Path, relative_doc_dir: str) -> Path:
        pack_root = pack_dir.resolve()
        doc_dir = (pack_root / relative_doc_dir).resolve()
        if not doc_dir.is_relative_to(pack_root):
            raise PathTraversalError(
                f"Knowledge document path escapes pack directory: {relative_doc_dir}"
            )
        return doc_dir

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
