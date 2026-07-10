# SPDX-License-Identifier: Apache-2.0

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field

from dream.core.errors import DreamError
from dream.core.paths import get_artifacts_dir

_REVOCATION_LEDGER_LOCK = Lock()


class AccessRevocationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    source_acl_version: str
    revoked_at: str
    revoked_by: str
    reason: str


class AccessRevocationLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "access-revocation-v1"
    events: list[AccessRevocationEvent] = Field(default_factory=list)


class AccessRevocationRegistry:
    """Persistent, team-scoped ACL-version revocation ledger."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_artifacts_dir() / "pilot-security/access-revocations.json"

    def revoke(
        self,
        *,
        team_id: str,
        source_acl_version: str,
        revoked_by: str,
        reason: str,
        revoked_at: str | None = None,
    ) -> AccessRevocationEvent:
        values = {
            "team_id": team_id.strip(),
            "source_acl_version": source_acl_version.strip(),
            "revoked_by": revoked_by.strip(),
            "reason": reason.strip(),
        }
        if any(not value for value in values.values()):
            raise ValueError("Revocation team, ACL version, actor, and reason are required.")
        event = AccessRevocationEvent(
            **values,
            revoked_at=revoked_at or datetime.now(UTC).isoformat(),
        )
        with _REVOCATION_LEDGER_LOCK:
            ledger = self.load()
            if not any(
                item.team_id == event.team_id
                and item.source_acl_version == event.source_acl_version
                for item in ledger.events
            ):
                ledger.events.append(event)
                ledger.events.sort(
                    key=lambda item: (
                        item.team_id,
                        item.source_acl_version,
                        item.revoked_at,
                    )
                )
                self._save(ledger)
        return event

    def is_revoked(self, *, team_id: str, acl_versions: set[str]) -> bool:
        if not acl_versions:
            return False
        revoked = {
            event.source_acl_version for event in self.load().events if event.team_id == team_id
        }
        return bool(revoked & acl_versions)

    def load(self) -> AccessRevocationLedger:
        if not self.path.exists():
            return AccessRevocationLedger()
        try:
            return AccessRevocationLedger.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DreamError("Access revocation ledger is unreadable or invalid.") from exc

    def _save(self, ledger: AccessRevocationLedger) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(ledger.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
