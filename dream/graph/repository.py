# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.errors import NotFoundError
from dream.core.paths import display_path, ensure_artifacts_dir
from dream.graph.models import EvidenceGraph


class EvidenceGraphRepository:
    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or ensure_artifacts_dir()

    def save(self, graph: EvidenceGraph) -> Path:
        path = self.graph_path(graph.team_id, graph.repo_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, team_id: str, repo_name: str | None = None) -> EvidenceGraph:
        path = self.graph_path(team_id, repo_name)
        if not path.exists():
            label = repo_name or "_team"
            raise NotFoundError(f"Evidence graph not found: {team_id}/{label}")
        return EvidenceGraph.model_validate_json(path.read_text(encoding="utf-8"))

    def try_load(self, team_id: str, repo_name: str | None = None) -> EvidenceGraph | None:
        path = self.graph_path(team_id, repo_name)
        if not path.exists():
            return None
        return EvidenceGraph.model_validate_json(path.read_text(encoding="utf-8"))

    def graph_path(self, team_id: str, repo_name: str | None = None) -> Path:
        safe_team = self._safe_name(team_id)
        safe_repo = self._safe_name(repo_name or "_team")
        return self.artifacts_dir / "evidence-graphs" / safe_team / f"{safe_repo}.json"

    def display_graph_path(self, team_id: str, repo_name: str | None = None) -> str:
        return display_path(self.graph_path(team_id, repo_name))

    def list_graph_names(self, team_id: str) -> list[str | None]:
        graph_dir = self.artifacts_dir / "evidence-graphs" / self._safe_name(team_id)
        if not graph_dir.exists():
            return []
        names: list[str | None] = []
        for path in sorted(graph_dir.glob("*.json")):
            names.append(None if path.stem == "_team" else path.stem)
        return names

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
