# SPDX-License-Identifier: Apache-2.0

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.codebase.language import detect_language
from dream.codebase.models import (
    ConceptMapping,
    DependencyEdge,
    FileNode,
    RepoIndex,
    SymbolNode,
    TestMapping,
)
from dream.codebase.repository import CodebaseIndexRepository
from dream.codebase.scanner import CodebaseScanner
from dream.codebase.summarizer import summarize_file, summarize_symbol
from dream.codebase.symbol_extractor import concepts_for_symbol, extract_symbols_and_dependencies
from dream.core.errors import DlpBlockedError
from dream.core.paths import display_path, resolve_project_path
from dream.dlp import DefaultDlpEngine
from dream.security.models import ResourceAccess


class CodebaseIndexer:
    def __init__(
        self,
        *,
        scanner: CodebaseScanner | None = None,
        repository: CodebaseIndexRepository | None = None,
        audit_logger: AuditLogger | None = None,
        dlp_engine: DefaultDlpEngine | None = None,
    ) -> None:
        self.scanner = scanner or CodebaseScanner()
        self.repository = repository or CodebaseIndexRepository()
        self.audit_logger = audit_logger or AuditLogger()
        self.dlp_engine = dlp_engine or DefaultDlpEngine()

    def index(
        self,
        *,
        team_id: str,
        repo_path: str | Path,
        repo_name: str | None = None,
        access: ResourceAccess | None = None,
    ) -> RepoIndex:
        root = resolve_project_path(repo_path, must_exist=True)
        name = repo_name or root.name
        repo_access = access or ResourceAccess()
        file_nodes = self.scanner.scan(root, access=repo_access)
        symbols: list[SymbolNode] = []
        dependencies: list[DependencyEdge] = []
        warnings: list[str] = []

        files_by_path = {file_node.path: file_node for file_node in file_nodes}
        for file_node in file_nodes:
            path = root / file_node.path
            try:
                raw_content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                warnings.append(f"Skipped non-UTF-8 file: {file_node.path}")
                continue
            try:
                inspection = self.dlp_engine.enforce(
                    raw_content,
                    stage="pre_index",
                    team_id=team_id,
                    resource_id=f"{name}:{file_node.path}",
                    classification=file_node.access.classification,
                )
            except DlpBlockedError:
                file_node.access = file_node.access.model_copy(update={"classification": "blocked"})
                warnings.append(f"DLP blocked file content from indexing: {file_node.path}")
                continue
            if inspection.evidence.redaction_count:
                warnings.append(
                    f"DLP redacted {inspection.evidence.redaction_count} finding(s) "
                    f"before indexing: {file_node.path}"
                )
            if detect_language(path) not in {"java", "python", "typescript"}:
                file_node.concepts = self._concepts_from_path(file_node.path)
                file_node.summary = summarize_file(file_node)
                continue
            extracted = extract_symbols_and_dependencies(
                language=file_node.language,
                path=path,
                relative_path=file_node.path,
                content=inspection.sanitized_text,
            )
            extracted_symbols, extracted_dependencies, concepts = extracted
            file_node.concepts = concepts
            for symbol in extracted_symbols:
                symbol.access = file_node.access.model_copy(deep=True)
                symbol.concepts = concepts_for_symbol(symbol, concepts)
                symbol.summary = summarize_symbol(symbol)
                symbols.append(symbol)
                file_node.symbols.append(symbol.symbol_id)
            dependencies.extend(extracted_dependencies)
            file_node.summary = summarize_file(file_node)

        indexable_files = [item for item in file_nodes if item.access.classification != "blocked"]
        tests = self._map_tests(indexable_files)
        for mapping in tests:
            source_access = files_by_path[mapping.source_file].access
            test_access = files_by_path[mapping.test_file].access
            mapping.access = source_access.restrictive_merge(test_access)
        dependencies.extend(self._test_dependencies(tests))
        concepts = self._build_concept_mappings(indexable_files, symbols, tests)
        for concept in concepts:
            concept.access = repo_access.model_copy(deep=True)
        index = RepoIndex(
            repo_id=self._stable_id(f"{team_id}:{name}:{display_path(root)}"),
            repo_name=name,
            repo_path=display_path(root),
            team_id=team_id,
            indexed_at=datetime.now(UTC).isoformat(),
            files=sorted(files_by_path.values(), key=lambda item: item.path),
            symbols=sorted(
                symbols,
                key=lambda item: (item.file_path, item.start_line or 0, item.name),
            ),
            tests=tests,
            dependencies=dependencies,
            concepts=concepts,
            summary=self._summary(name, file_nodes, symbols, tests, concepts),
            warnings=warnings,
            access=repo_access.model_copy(deep=True),
        )
        output_path = self.repository.save(index)
        self.audit_logger.log_generation(
            run_id=f"codebase-index-{uuid4().hex[:12]}",
            use_case="codebase_index",
            team_id=team_id,
            input_payload={"team_id": team_id, "repo_path": str(repo_path), "repo_name": name},
            retrieved_source_paths=[file_node.path for file_node in file_nodes],
            model_provider="deterministic",
            model_name="codebase-indexer-v1",
            output_path=display_path(output_path),
            status="success",
            warnings=warnings,
            repo_name=name,
        )
        return index

    @staticmethod
    def _concepts_from_path(path: str) -> list[str]:
        tokens = path.replace("/", " ").replace("-", " ").replace("_", " ").lower().split()
        allowed = {"docs", "config", "test", "job", "status"}
        concepts = {token for token in tokens if token in allowed}
        return sorted(concepts)

    @staticmethod
    def _map_tests(files: list[FileNode]) -> list[TestMapping]:
        source_files = [file_node for file_node in files if file_node.role == "source"]
        test_files = [file_node for file_node in files if file_node.role == "test"]
        mappings: list[TestMapping] = []
        for source in source_files:
            source_stem = Path(source.path).stem
            candidates = [
                test
                for test in test_files
                if Path(test.path).stem.lower()
                in {f"{source_stem}test".lower(), source_stem.lower()}
                or source_stem.lower() in Path(test.path).stem.lower()
            ]
            if not candidates:
                continue
            candidate = sorted(candidates, key=lambda item: item.path)[0]
            mappings.append(
                TestMapping(
                    source_file=source.path,
                    test_file=candidate.path,
                    confidence=0.9,
                    reason="Matched source basename to test basename.",
                )
            )
        return sorted(mappings, key=lambda item: (item.source_file, item.test_file))

    @staticmethod
    def _test_dependencies(tests: list[TestMapping]) -> list[DependencyEdge]:
        return [
            DependencyEdge(
                from_file=mapping.test_file,
                to_file=mapping.source_file,
                dependency_type="test",
                confidence=mapping.confidence,
            )
            for mapping in tests
        ]

    @staticmethod
    def _build_concept_mappings(
        files: list[FileNode],
        symbols: list[SymbolNode],
        tests: list[TestMapping],
    ) -> list[ConceptMapping]:
        related_files: dict[str, set[str]] = defaultdict(set)
        related_symbols: dict[str, set[str]] = defaultdict(set)
        related_tests: dict[str, set[str]] = defaultdict(set)
        test_by_source = {mapping.source_file: mapping.test_file for mapping in tests}

        for file_node in files:
            for concept in file_node.concepts:
                related_files[concept].add(file_node.path)
                if file_node.path in test_by_source:
                    related_tests[concept].add(test_by_source[file_node.path])
                if file_node.role == "test":
                    related_tests[concept].add(file_node.path)
        for symbol in symbols:
            for concept in symbol.concepts:
                related_symbols[concept].add(symbol.name)
                related_files[concept].add(symbol.file_path)
                if symbol.file_path in test_by_source:
                    related_tests[concept].add(test_by_source[symbol.file_path])

        mappings: list[ConceptMapping] = []
        for concept in sorted(set(related_files) | set(related_symbols)):
            mappings.append(
                ConceptMapping(
                    concept=concept,
                    related_files=sorted(related_files[concept]),
                    related_symbols=sorted(related_symbols[concept]),
                    related_tests=sorted(related_tests[concept]),
                    confidence=0.75,
                    reason="Derived from file paths, symbols, and repeated domain tokens.",
                )
            )
        return mappings

    @staticmethod
    def _summary(
        repo_name: str,
        files: list[FileNode],
        symbols: list[SymbolNode],
        tests: list[TestMapping],
        concepts: list[ConceptMapping],
    ) -> str:
        languages = sorted(
            {file_node.language for file_node in files if file_node.language != "unknown"}
        )
        top_concepts = ", ".join(concept.concept for concept in concepts[:6]) or "general code"
        return (
            f"{repo_name} index contains {len(files)} files, {len(symbols)} symbols, "
            f"{len(tests)} source-to-test mappings, and languages: {', '.join(languages)}. "
            f"Top concepts: {top_concepts}."
        )

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
