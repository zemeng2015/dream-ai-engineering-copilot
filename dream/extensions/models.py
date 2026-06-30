# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from typing import Protocol

from dream.audit.models import AuditRecord
from dream.codebase.models import CodebaseSearchResult, RepoIndex
from dream.knowledge.models import TeamKnowledgePack
from dream.llm.base import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        """Return a completion for the supplied prompt."""


class KnowledgePackProvider(Protocol):
    def list_team_ids(self) -> list[str]:
        """Return available knowledge pack team IDs."""

    def load(self, team_id: str) -> TeamKnowledgePack:
        """Load one knowledge pack."""

    def pack_dir(self, team_id: str) -> Path:
        """Return the on-disk directory for a team knowledge pack."""


class ArtifactStore(Protocol):
    root: Path

    def resolve_path(self, relative_path: str | Path) -> Path:
        """Resolve a path safely under the artifact root."""

    def write_text(self, relative_path: str | Path, content: str) -> Path:
        """Write UTF-8 text under the artifact root."""

    def read_text(self, relative_path: str | Path) -> str:
        """Read UTF-8 text from the artifact root."""


class RedactionProvider(Protocol):
    provider_name: str

    def redact(self, text: str) -> str:
        """Return text with sensitive values removed."""


class PromptPolicyProvider(Protocol):
    provider_name: str

    def apply(self, prompt: str) -> str:
        """Apply prompt policy before provider invocation."""


class CodebaseMemoryProvider(Protocol):
    provider_name: str

    def index_repository(
        self,
        team_id: str,
        repo_path: str | Path,
        repo_name: str | None = None,
    ) -> RepoIndex:
        """Index a repository into codebase memory."""

    def load_index(self, team_id: str, repo_name: str) -> RepoIndex:
        """Load a codebase memory index."""

    def search(
        self,
        team_id: str,
        repo_name: str,
        query: str,
        top_k: int = 5,
    ) -> list[CodebaseSearchResult]:
        """Search codebase memory."""

    def explain_file(self, team_id: str, repo_name: str, file_path: str) -> dict[str, object]:
        """Explain a file from codebase memory."""

    def find_related_tests(self, team_id: str, repo_name: str, source_file: str) -> list[str]:
        """Find tests related to a source file."""

    def estimate_impact_for_changed_files(
        self,
        team_id: str,
        repo_name: str,
        changed_files: list[str],
    ) -> list[CodebaseSearchResult]:
        """Estimate impact for changed files."""

    def export_relationships(self, team_id: str, repo_name: str) -> dict[str, object]:
        """Export codebase relationships for Evidence Graph Lite."""


class AuditSink(Protocol):
    def record(self, record: AuditRecord) -> None:
        """Persist an audit record."""
