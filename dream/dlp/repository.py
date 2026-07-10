# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from threading import Lock

from dream.core.errors import DreamError
from dream.core.paths import ensure_artifacts_dir
from dream.dlp.models import DlpDecisionEvidence, DlpEventLedger

_DLP_LEDGER_LOCK = Lock()


class DlpEventRepository:
    """Append-only metadata evidence ledger for local DLP boundary decisions."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        root = (artifacts_dir or ensure_artifacts_dir()).resolve()
        self.path = root / "pilot-security/dlp-events.jsonl"

    def record(self, event: DlpDecisionEvidence) -> None:
        with _DLP_LEDGER_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(event.model_dump_json() + "\n")

    def load(self) -> DlpEventLedger:
        if not self.path.exists():
            return DlpEventLedger()
        try:
            events = [
                DlpDecisionEvidence.model_validate_json(line)
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            return DlpEventLedger(
                events=sorted(events, key=lambda item: (item.timestamp, item.event_id))
            )
        except (OSError, ValueError) as exc:
            raise DreamError("DLP event ledger is unreadable or invalid.") from exc
