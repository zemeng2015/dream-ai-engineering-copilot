# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.codebase.models import RepoIndex
from dream.core.errors import NotFoundError
from dream.core.paths import display_path, ensure_artifacts_dir


class CodebaseIndexRepository:
    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or ensure_artifacts_dir()

    def save(self, index: RepoIndex) -> Path:
        path = self.index_path(index.team_id, index.repo_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, team_id: str, repo_name: str) -> RepoIndex:
        path = self.index_path(team_id, repo_name)
        if not path.exists():
            raise NotFoundError(f"Codebase index not found for {team_id}/{repo_name}")
        return RepoIndex.model_validate_json(path.read_text(encoding="utf-8"))

    def try_load(self, team_id: str, repo_name: str) -> RepoIndex | None:
        path = self.index_path(team_id, repo_name)
        if not path.exists():
            return None
        return RepoIndex.model_validate_json(path.read_text(encoding="utf-8"))

    def list_repo_names(self, team_id: str) -> list[str]:
        base_dir = self.artifacts_dir / "codebase-indexes" / self._safe_name(team_id)
        if not base_dir.exists():
            return []
        return sorted(path.stem for path in base_dir.glob("*.json"))

    def index_path(self, team_id: str, repo_name: str) -> Path:
        safe_team = self._safe_name(team_id)
        safe_repo_name = self._safe_name(Path(repo_name).name.replace(" ", "-"))
        return self.artifacts_dir / "codebase-indexes" / safe_team / f"{safe_repo_name}.json"

    def display_index_path(self, team_id: str, repo_name: str) -> str:
        return display_path(self.index_path(team_id, repo_name))

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
