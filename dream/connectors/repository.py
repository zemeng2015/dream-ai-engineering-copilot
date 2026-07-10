# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from threading import Lock

from dream.connectors.models import (
    ConnectorLifecycleEvent,
    ConnectorLifecycleLedger,
    ConnectorSourceState,
    connector_source_key,
)
from dream.core.errors import DreamError, NotFoundError
from dream.core.paths import ensure_artifacts_dir

_LEDGER_LOCK = Lock()


class ConnectorLifecycleRepository:
    """Persistent metadata-only source state and lifecycle event ledger."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = (artifacts_dir or ensure_artifacts_dir()).resolve()
        self.path = self.artifacts_dir / "pilot-security/connector-source-lifecycle.json"

    def get(self, *, team_id: str, connector_id: str, source_id: str) -> ConnectorSourceState:
        source_key = connector_source_key(
            team_id=team_id,
            connector_id=connector_id,
            source_id=source_id,
        )
        for state in self.load().states:
            if state.source_key == source_key:
                return state
        raise NotFoundError(f"Connector source not found: {source_key}")

    def try_get(
        self,
        *,
        team_id: str,
        connector_id: str,
        source_id: str,
    ) -> ConnectorSourceState | None:
        try:
            return self.get(team_id=team_id, connector_id=connector_id, source_id=source_id)
        except NotFoundError:
            return None

    def record(
        self,
        *,
        state: ConnectorSourceState,
        event: ConnectorLifecycleEvent,
    ) -> None:
        with _LEDGER_LOCK:
            ledger = self.load()
            ledger.states = [item for item in ledger.states if item.source_key != state.source_key]
            ledger.states.append(state)
            ledger.states.sort(key=lambda item: item.source_key)
            ledger.events.append(event)
            ledger.events.sort(key=lambda item: (item.occurred_at, item.event_id))
            self._save(ledger)

    def load(self) -> ConnectorLifecycleLedger:
        if not self.path.exists():
            return ConnectorLifecycleLedger()
        try:
            return ConnectorLifecycleLedger.model_validate_json(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise DreamError("Connector source lifecycle ledger is unreadable or invalid.") from exc

    def _save(self, ledger: ConnectorLifecycleLedger) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(ledger.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
