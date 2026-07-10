# SPDX-License-Identifier: Apache-2.0

import os
import re
from pathlib import Path

from dream.audit.models import AuditRecord
from dream.audit.repository import AuditRepository
from dream.codebase.indexer import CodebaseIndexer
from dream.codebase.models import CodebaseSearchResult
from dream.codebase.repository import CodebaseIndexRepository
from dream.codebase.retriever import CodebaseRetriever
from dream.config.loader import resolve_config
from dream.config.models import DreamConfig, ResolvedDreamConfig
from dream.core.errors import PathTraversalError
from dream.dlp import ensure_dlp_guarded_provider
from dream.extensions.loader import load_instance
from dream.knowledge.pack_loader import KnowledgePackLoader
from dream.llm import MockLLMProvider, OpenAICompatibleProvider, QwenCloudProvider


class LocalArtifactStore:
    provider_name = "local-artifact-store"

    def __init__(self, root: str | Path | None = None) -> None:
        config_root = resolve_config().artifacts.root if root is None else root
        self.root = Path(config_root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_path: str | Path) -> Path:
        raw_path = Path(relative_path)
        candidate = raw_path if raw_path.is_absolute() else self.root / raw_path
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise PathTraversalError(f"Artifact path escapes artifact root: {relative_path}")
        return resolved

    def write_text(self, relative_path: str | Path, content: str) -> Path:
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_text(self, relative_path: str | Path) -> str:
        return self.resolve_path(relative_path).read_text(encoding="utf-8")


class LocalKnowledgePackProvider:
    provider_name = "local-knowledge-pack"

    def __init__(self, root: str | Path | None = None) -> None:
        self.loader = KnowledgePackLoader(packs_dir=Path(root) if root is not None else None)

    def list_team_ids(self) -> list[str]:
        return self.loader.list_team_ids()

    def load(self, team_id: str):
        return self.loader.load(team_id)

    def pack_dir(self, team_id: str) -> Path:
        return self.loader.pack_dir(team_id)


class DefaultRedactionProvider:
    provider_name = "default"

    _secret_patterns = [
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token|private[_-]?key)"
            r"(\s*[:=]\s*)([^\s,;\"']+)"
        ),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ]

    def redact(self, text: str) -> str:
        redacted = self._secret_patterns[0].sub(
            lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
            text,
        )
        redacted = self._secret_patterns[1].sub("[REDACTED_AWS_ACCESS_KEY]", redacted)
        return self._secret_patterns[2].sub("[REDACTED_JWT]", redacted)


class DefaultPromptPolicyProvider:
    provider_name = "default"

    def apply(self, prompt: str) -> str:
        return prompt


class SQLiteAuditSink:
    provider_name = "sqlite"

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.repository = AuditRepository(Path(db_path) if db_path is not None else None)

    def record(self, record: AuditRecord) -> None:
        self.repository.add_audit_record(record)


class NativeCodebaseMemoryProvider:
    provider_name = "native"

    def __init__(self, repository: CodebaseIndexRepository | None = None) -> None:
        self.repository = repository or CodebaseIndexRepository()
        self.retriever = CodebaseRetriever(repository=self.repository)

    def index_repository(
        self,
        team_id: str,
        repo_path: str | Path,
        repo_name: str | None = None,
    ):
        return CodebaseIndexer(repository=self.repository).index(
            team_id=team_id,
            repo_path=repo_path,
            repo_name=repo_name,
        )

    def load_index(self, team_id: str, repo_name: str):
        return self.repository.load(team_id, repo_name)

    def search(self, team_id: str, repo_name: str, query: str, top_k: int = 5):
        return self.retriever.search(team_id=team_id, repo_name=repo_name, query=query, top_k=top_k)

    def explain_file(self, team_id: str, repo_name: str, file_path: str) -> dict[str, object]:
        file_node = self.retriever.find_file(
            team_id=team_id,
            repo_name=repo_name,
            file_path=file_path,
        )
        if file_node is None:
            return {"found": False, "file_path": file_path, "related_tests": []}
        related_tests = self.find_related_tests(team_id, repo_name, file_node.path)
        return {
            "found": True,
            "file_path": file_node.path,
            "language": file_node.language,
            "role": file_node.role,
            "summary": file_node.summary,
            "concepts": file_node.concepts,
            "symbols": file_node.symbols,
            "related_tests": related_tests,
        }

    def find_related_tests(self, team_id: str, repo_name: str, source_file: str) -> list[str]:
        return [
            mapping.test_file
            for mapping in self.retriever.find_tests_for_source(
                team_id=team_id,
                repo_name=repo_name,
                source_file=source_file,
            )
        ]

    def estimate_impact_for_changed_files(
        self,
        team_id: str,
        repo_name: str,
        changed_files: list[str],
    ) -> list[CodebaseSearchResult]:
        index = self.repository.try_load(team_id, repo_name)
        if index is None:
            return []
        results: list[CodebaseSearchResult] = []
        for file_path in changed_files:
            file_node = self.retriever.find_file(
                team_id=team_id,
                repo_name=repo_name,
                file_path=file_path,
            )
            if file_node is None:
                continue
            results.append(
                CodebaseSearchResult(
                    result_type="changed_file",
                    title=file_node.path,
                    source_path=file_node.path,
                    excerpt=file_node.summary or "",
                    score=100,
                    reason="File was directly changed.",
                    metadata={"language": file_node.language, "role": file_node.role},
                )
            )
            for concept in file_node.concepts:
                results.extend(
                    self.retriever.related_to_concept(
                        team_id=team_id,
                        repo_name=repo_name,
                        concept=concept,
                    )
                )
        seen: set[tuple[str, str]] = set()
        deduped: list[CodebaseSearchResult] = []
        for result in sorted(results, key=lambda item: (-item.score, item.source_path)):
            key = (result.result_type, result.source_path)
            if key not in seen:
                seen.add(key)
                deduped.append(result)
        return deduped

    def export_relationships(self, team_id: str, repo_name: str) -> dict[str, object]:
        index = self.repository.load(team_id, repo_name)
        return {
            "team_id": team_id,
            "repo_name": repo_name,
            "files": [file_node.model_dump() for file_node in index.files],
            "symbols": [symbol.model_dump() for symbol in index.symbols],
            "tests": [mapping.model_dump() for mapping in index.tests],
            "dependencies": [edge.model_dump() for edge in index.dependencies],
            "concepts": [concept.model_dump() for concept in index.concepts],
        }


def build_llm_provider(config: DreamConfig | ResolvedDreamConfig | None = None):
    resolved = config if isinstance(config, ResolvedDreamConfig) else resolve_config(config)
    if resolved.llm.provider == "mock":
        provider = MockLLMProvider()
    elif resolved.llm.provider == "openai-compatible":
        api_key = os.getenv(resolved.llm.api_key_env) if resolved.llm.api_key_env else None
        provider = OpenAICompatibleProvider(
            api_key=api_key,
            base_url=resolved.llm.base_url,
            model_name=resolved.llm.model,
        )
    elif resolved.llm.provider == "qwen-cloud":
        api_key = os.getenv(resolved.llm.api_key_env) if resolved.llm.api_key_env else None
        provider = QwenCloudProvider(
            api_key=api_key,
            base_url=resolved.llm.base_url,
            model_name=resolved.llm.model,
        )
    elif resolved.llm.provider == "plugin" and resolved.llm.class_path:
        provider = load_instance(resolved.llm.class_path)
    else:
        raise ValueError(f"Unsupported LLM provider: {resolved.llm.provider}")
    return ensure_dlp_guarded_provider(provider)


def build_redaction_provider(config: DreamConfig | ResolvedDreamConfig | None = None):
    resolved = config if isinstance(config, ResolvedDreamConfig) else resolve_config(config)
    if resolved.redaction.provider == "default":
        return DefaultRedactionProvider()
    if resolved.redaction.class_path:
        return load_instance(resolved.redaction.class_path)
    raise ValueError("Redaction plugin provider requires class_path.")


def build_prompt_policy_provider(config: DreamConfig | ResolvedDreamConfig | None = None):
    resolved = config if isinstance(config, ResolvedDreamConfig) else resolve_config(config)
    if resolved.prompt_policy.provider == "default":
        return DefaultPromptPolicyProvider()
    if resolved.prompt_policy.class_path:
        return load_instance(resolved.prompt_policy.class_path)
    raise ValueError("Prompt policy plugin provider requires class_path.")
