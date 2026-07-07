# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.errors import NotFoundError
from dream.core.paths import display_path, ensure_artifacts_dir
from dream.memory.models import (
    MemoryConflictResolutionEvent,
    MemoryConflictResolutionLedger,
    MemoryEvalResult,
    MemoryLedgerSnapshot,
    MemoryReviewEvent,
    MemoryScanResult,
)


class MemoryDistillationRepository:
    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or ensure_artifacts_dir()

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

    def list_scans(self, team_id: str) -> list[MemoryScanResult]:
        scan_dir = self._scan_dir(team_id)
        if not scan_dir.exists():
            return []
        scans = []
        for path in scan_dir.glob("*.json"):
            if path.name == "latest.json":
                continue
            scans.append(MemoryScanResult.model_validate_json(path.read_text(encoding="utf-8")))
        return sorted(scans, key=lambda scan: (scan.created_at, scan.scan_id))

    def previous_scan(self, team_id: str, scan_id: str) -> MemoryScanResult | None:
        target = self.load_scan(team_id, scan_id)
        previous = [
            scan
            for scan in self.list_scans(team_id)
            if (scan.created_at, scan.scan_id) < (target.created_at, target.scan_id)
        ]
        return previous[-1] if previous else None

    def save_eval(self, result: MemoryEvalResult) -> Path:
        path = self.eval_path(result.team_id, result.evaluation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return path

    def append_review_event(self, event: MemoryReviewEvent) -> Path:
        ledger = self.load_ledger(event.team_id)
        ledger.events.append(event)
        ledger.updated_at = event.reviewed_at
        return self.save_ledger(ledger)

    def append_conflict_resolution_event(
        self,
        event: MemoryConflictResolutionEvent,
    ) -> Path:
        ledger = self.load_conflict_resolution_ledger(event.team_id)
        ledger.events.append(event)
        ledger.updated_at = event.resolved_at
        return self.save_conflict_resolution_ledger(ledger)

    def save_ledger(self, ledger: MemoryLedgerSnapshot) -> Path:
        path = self.ledger_path(ledger.team_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
        return path

    def save_conflict_resolution_ledger(
        self,
        ledger: MemoryConflictResolutionLedger,
    ) -> Path:
        path = self.conflict_resolution_ledger_path(ledger.team_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_ledger(self, team_id: str) -> MemoryLedgerSnapshot:
        path = self.ledger_path(team_id)
        if not path.exists():
            return MemoryLedgerSnapshot(team_id=team_id, updated_at="", events=[])
        return MemoryLedgerSnapshot.model_validate_json(path.read_text(encoding="utf-8"))

    def load_conflict_resolution_ledger(
        self,
        team_id: str,
    ) -> MemoryConflictResolutionLedger:
        path = self.conflict_resolution_ledger_path(team_id)
        if not path.exists():
            return MemoryConflictResolutionLedger(team_id=team_id, updated_at="", events=[])
        return MemoryConflictResolutionLedger.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def latest_review_statuses(self, team_id: str) -> dict[str, MemoryReviewEvent]:
        latest: dict[str, MemoryReviewEvent] = {}
        for event in self.load_ledger(team_id).events:
            latest[event.claim_id] = event
        return latest

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

    def ledger_path(self, team_id: str) -> Path:
        return self.artifacts_dir / "memory-ledgers" / f"{self._safe_name(team_id)}.json"

    def conflict_resolution_ledger_path(self, team_id: str) -> Path:
        return (
            self.artifacts_dir
            / "memory-conflict-resolutions"
            / f"{self._safe_name(team_id)}.json"
        )

    def display_scan_path(self, team_id: str, scan_id: str) -> str:
        return display_path(self.scan_path(team_id, scan_id))

    def display_latest_scan_path(self, team_id: str) -> str:
        return display_path(self.latest_scan_path(team_id))

    def display_eval_path(self, team_id: str, evaluation_id: str) -> str:
        return display_path(self.eval_path(team_id, evaluation_id))

    def display_ledger_path(self, team_id: str) -> str:
        return display_path(self.ledger_path(team_id))

    def display_conflict_resolution_ledger_path(self, team_id: str) -> str:
        return display_path(self.conflict_resolution_ledger_path(team_id))

    def _scan_dir(self, team_id: str) -> Path:
        return self.artifacts_dir / "memory-scans" / self._safe_name(team_id)

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")
