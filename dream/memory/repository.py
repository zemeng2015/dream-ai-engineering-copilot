# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.errors import NotFoundError
from dream.core.paths import ARTIFACTS_DIR, display_path
from dream.memory.models import MemoryEvalResult, MemoryScanResult


class MemoryDistillationRepository:
    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR) -> None:
        self.artifacts_dir = artifacts_dir

    def save_scan(self, scan: MemoryScanResult) -> Path:
        path = self.scan_path(scan.team_id, scan.scan_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = scan.model_dump_json(indent=2)
        path.write_text(payload, encoding="utf-8")
        self.latest_scan_path(scan.team_id).write_text(payload, encoding="utf-8")
        return path

    def load_scan(self, team_id: str, scan_id: str) -> MemoryScanResult:
        path = (
            self.latest_scan_path(team_id)
            if scan_id == "latest"
            else self.scan_path(team_id, scan_id)
        )
        if not path.exists():
            raise NotFoundError(f"Memory scan not found: {team_id}/{scan_id}")
        return MemoryScanResult.model_validate_json(path.read_text(encoding="utf-8"))

    def try_load_latest_scan(self, team_id: str) -> MemoryScanResult | None:
        path = self.latest_scan_path(team_id)
        if not path.exists():
            return None
        return MemoryScanResult.model_validate_json(path.read_text(encoding="utf-8"))

    def save_eval(self, result: MemoryEvalResult) -> Path:
        path = self.eval_path(result.team_id, result.evaluation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return path

    def scan_path(self, team_id: str, scan_id: str) -> Path:
        return self._scan_dir(team_id) / f"{self._safe_name(scan_id)}.json"

    def latest_scan_path(self, team_id: str) -> Path:
        return self._scan_dir(team_id) / "latest.json"

    def eval_path(self, team_id: str, evaluation_id: str) -> Path:
        return (
            self.artifacts_dir
            / "memory-evals"
            / self._safe_name(team_id)
            / f"{self._safe_name(evaluation_id)}.json"
        )

    def display_scan_path(self, team_id: str, scan_id: str) -> str:
        return display_path(self.scan_path(team_id, scan_id))

    def display_latest_scan_path(self, team_id: str) -> str:
        return display_path(self.latest_scan_path(team_id))

    def display_eval_path(self, team_id: str, evaluation_id: str) -> str:
        return display_path(self.eval_path(team_id, evaluation_id))

    def _scan_dir(self, team_id: str) -> Path:
        return self.artifacts_dir / "memory-scans" / self._safe_name(team_id)

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
