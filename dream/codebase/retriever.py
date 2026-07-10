# SPDX-License-Identifier: Apache-2.0

import re

from dream.codebase.models import CodebaseSearchResult, FileNode, RepoIndex, SymbolNode, TestMapping
from dream.codebase.repository import CodebaseIndexRepository
from dream.security import AccessContext, DefaultAccessPolicy, ResourceAccess

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class CodebaseRetriever:
    def __init__(
        self,
        repository: CodebaseIndexRepository | None = None,
        *,
        access_policy: DefaultAccessPolicy | None = None,
    ) -> None:
        self.repository = repository or CodebaseIndexRepository()
        self.access_policy = access_policy or DefaultAccessPolicy()

    def search(
        self,
        *,
        team_id: str,
        repo_name: str,
        query: str,
        top_k: int = 5,
        access_context: AccessContext | None = None,
    ) -> list[CodebaseSearchResult]:
        index = self.repository.try_load(team_id, repo_name)
        if index is None:
            return []
        return self.search_index(
            index=index,
            query=query,
            top_k=top_k,
            access_context=access_context,
        )

    def search_index(
        self,
        *,
        index: RepoIndex,
        query: str,
        top_k: int = 5,
        access_context: AccessContext | None = None,
    ) -> list[CodebaseSearchResult]:
        context = access_context or AccessContext.public_demo(team_ids={index.team_id})
        if not self._readable(
            context=context,
            team_id=index.team_id,
            access=index.access,
            resource_id=index.repo_id,
        ):
            return []
        terms = self._tokens(query)
        scored: list[tuple[int, str, CodebaseSearchResult]] = []
        for file_node in index.files:
            if not self._readable(
                context=context,
                team_id=index.team_id,
                access=file_node.access,
                resource_id=file_node.file_id,
            ):
                continue
            score = self._score_file(file_node, terms)
            if score > 0:
                scored.append((score, file_node.path, self._file_result(file_node, score, terms)))
        for symbol in index.symbols:
            if not self._readable(
                context=context,
                team_id=index.team_id,
                access=symbol.access,
                resource_id=symbol.symbol_id,
            ):
                continue
            score = self._score_symbol(symbol, terms)
            if score > 0:
                scored.append(
                    (
                        score,
                        f"{symbol.file_path}:{symbol.name}",
                        self._symbol_result(symbol, score),
                    )
                )
        for concept in index.concepts:
            if not self._readable(
                context=context,
                team_id=index.team_id,
                access=concept.access,
                resource_id=f"concept:{concept.concept}",
            ):
                continue
            score = self._score_text(
                " ".join(
                    [
                        concept.concept,
                        " ".join(concept.related_files),
                        " ".join(concept.related_symbols),
                    ]
                ),
                terms,
            )
            if score > 0:
                scored.append(
                    (
                        score,
                        f"concept:{concept.concept}",
                        CodebaseSearchResult(
                            result_type="concept",
                            title=concept.concept,
                            source_path=f"{index.repo_name}#concept:{concept.concept}",
                            excerpt=concept.reason,
                            score=score,
                            reason="Concept matched query terms.",
                            metadata={"repo_name": index.repo_name, "team_id": index.team_id},
                            access=concept.access.model_copy(deep=True),
                        ),
                    )
                )
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:top_k]]

    def find_tests_for_source(
        self,
        *,
        team_id: str,
        repo_name: str,
        source_file: str,
        access_context: AccessContext | None = None,
    ) -> list[TestMapping]:
        index = self.repository.try_load(team_id, repo_name)
        if index is None:
            return []
        context = access_context or AccessContext.public_demo(team_ids={team_id})
        if not self._readable(
            context=context,
            team_id=team_id,
            access=index.access,
            resource_id=index.repo_id,
        ):
            return []
        files_by_path = {item.path: item for item in index.files}
        mappings = []
        for mapping in index.tests:
            if not (
                mapping.source_file == source_file or mapping.source_file.endswith(source_file)
            ):
                continue
            source = files_by_path.get(mapping.source_file)
            test = files_by_path.get(mapping.test_file)
            if source is None or test is None:
                continue
            if self._readable(
                context=context,
                team_id=team_id,
                access=source.access,
                resource_id=source.file_id,
            ) and self._readable(
                context=context,
                team_id=team_id,
                access=test.access,
                resource_id=test.file_id,
            ):
                mappings.append(mapping)
        return mappings

    def find_file(
        self,
        *,
        team_id: str,
        repo_name: str,
        file_path: str,
        access_context: AccessContext | None = None,
    ) -> FileNode | None:
        index = self.repository.try_load(team_id, repo_name)
        if index is None:
            return None
        normalized = file_path.replace("\\", "/")
        context = access_context or AccessContext.public_demo(team_ids={team_id})
        if not self._readable(
            context=context,
            team_id=team_id,
            access=index.access,
            resource_id=index.repo_id,
        ):
            return None
        for file_node in index.files:
            if (
                file_node.path == normalized or file_node.path.endswith(normalized)
            ) and self._readable(
                context=context,
                team_id=team_id,
                access=file_node.access,
                resource_id=file_node.file_id,
            ):
                return file_node
        return None

    def related_to_concept(
        self,
        *,
        team_id: str,
        repo_name: str,
        concept: str,
        access_context: AccessContext | None = None,
    ) -> list[CodebaseSearchResult]:
        index = self.repository.try_load(team_id, repo_name)
        if index is None:
            return []
        normalized = concept.lower()
        context = access_context or AccessContext.public_demo(team_ids={team_id})
        if not self._readable(
            context=context,
            team_id=team_id,
            access=index.access,
            resource_id=index.repo_id,
        ):
            return []
        results: list[CodebaseSearchResult] = []
        for mapping in index.concepts:
            if normalized in mapping.concept.lower() and self._readable(
                context=context,
                team_id=team_id,
                access=mapping.access,
                resource_id=f"concept:{mapping.concept}",
            ):
                results.append(
                    CodebaseSearchResult(
                        result_type="concept",
                        title=mapping.concept,
                        source_path=f"{repo_name}#concept:{mapping.concept}",
                        excerpt=", ".join(mapping.related_files[:5]),
                        score=10,
                        reason=mapping.reason,
                        metadata={"repo_name": repo_name, "team_id": team_id},
                        access=mapping.access.model_copy(deep=True),
                    )
                )
        return results

    def _readable(
        self,
        *,
        context: AccessContext,
        team_id: str,
        access: ResourceAccess,
        resource_id: str,
    ) -> bool:
        return self.access_policy.decide(
            context=context,
            team_id=team_id,
            action="retrieve",
            resource_access=access,
            resource_id=resource_id,
        ).allowed

    @staticmethod
    def _file_result(file_node: FileNode, score: int, terms: list[str]) -> CodebaseSearchResult:
        matched = sorted(set(terms) & set(CodebaseRetriever._tokens(file_node.path)))
        reason = f"Matched file path/concepts/summary terms: {', '.join(matched) or 'content'}."
        return CodebaseSearchResult(
            result_type="code_file" if file_node.role != "test" else "test_file",
            title=file_node.path,
            source_path=file_node.path,
            excerpt=file_node.summary or "",
            score=score,
            reason=reason,
            metadata={"language": file_node.language, "role": file_node.role},
            access=file_node.access.model_copy(deep=True),
        )

    @staticmethod
    def _symbol_result(symbol: SymbolNode, score: int) -> CodebaseSearchResult:
        return CodebaseSearchResult(
            result_type="code_symbol",
            title=f"{symbol.name} ({symbol.kind})",
            source_path=symbol.file_path,
            excerpt=symbol.summary or symbol.signature or "",
            score=score,
            reason="Matched symbol name, signature, concepts, or summary.",
            metadata={"symbol_id": symbol.symbol_id, "kind": symbol.kind},
            access=symbol.access.model_copy(deep=True),
        )

    @classmethod
    def _score_file(cls, file_node: FileNode, terms: list[str]) -> int:
        text = " ".join(
            [
                file_node.path,
                file_node.language,
                file_node.role,
                file_node.summary or "",
                " ".join(file_node.concepts),
            ]
        )
        return cls._score_text(text, terms)

    @classmethod
    def _score_symbol(cls, symbol: SymbolNode, terms: list[str]) -> int:
        text = " ".join(
            [
                symbol.name,
                symbol.kind,
                symbol.file_path,
                symbol.signature or "",
                symbol.summary or "",
                " ".join(symbol.concepts),
            ]
        )
        return cls._score_text(text, terms)

    @staticmethod
    def _score_text(text: str, terms: list[str]) -> int:
        tokens = CodebaseRetriever._tokens(text)
        return sum(tokens.count(term) for term in terms)

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [token.lower() for token in TOKEN_RE.findall(value)]
