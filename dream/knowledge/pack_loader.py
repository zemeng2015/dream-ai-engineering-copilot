# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import yaml

from dream.core.errors import NotFoundError, PathTraversalError
from dream.core.paths import get_knowledge_packs_dir
from dream.knowledge.models import TeamKnowledgePack


class KnowledgePackLoader:
    def __init__(self, packs_dir: Path | None = None) -> None:
        self.packs_dir = packs_dir or get_knowledge_packs_dir()

    def list_team_ids(self) -> list[str]:
        if not self.packs_dir.exists():
            return []
        team_ids: list[str] = []
        for team_file in sorted(self.packs_dir.glob("*/team.yaml")):
            data = self._read_yaml(team_file)
            team_id = data.get("team_id")
            if team_id:
                team_ids.append(str(team_id))
        return team_ids

    def load(self, team_id: str) -> TeamKnowledgePack:
        team_file = self.pack_dir(team_id) / "team.yaml"
        if not team_file.exists():
            raise NotFoundError(f"Knowledge pack not found for team: {team_id}")
        return TeamKnowledgePack.model_validate(self._read_yaml(team_file))

    def pack_dir(self, team_id: str) -> Path:
        packs_root = self.packs_dir.resolve()
        pack_dir = (packs_root / team_id).resolve()
        if not pack_dir.is_relative_to(packs_root):
            raise PathTraversalError(f"Knowledge pack escapes packs directory: {team_id}")
        return pack_dir

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, object]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected mapping in {path}")
        return data
