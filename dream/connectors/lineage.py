# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from dream.connectors.models import (
    ArtifactLineageLedger,
    ArtifactLineageRecord,
    ArtifactPurgeItem,
    ArtifactPurgeReport,
)
from dream.core.errors import DreamError, NotFoundError, PathTraversalError
from dream.core.paths import ensure_artifacts_dir
from dream.security.models import ResourceAccess

_LINEAGE_LOCK = Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ArtifactLineageRegistry:
    """Exact derived-artifact locators indexed by source ACL version lineage."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = (artifacts_dir or ensure_artifacts_dir()).resolve()
        self.path = self.artifacts_dir / "pilot-security/artifact-lineage.json"

    def register_path(
        self,
        *,
        team_id: str,
        artifact_kind: str,
        path: Path,
        access: ResourceAccess | None = None,
        acl_versions: set[str] | None = None,
        directory: bool = False,
        must_exist: bool = False,
    ) -> ArtifactLineageRecord | None:
        versions = set(acl_versions or set())
        if access is not None:
            versions.update(access.acl_versions())
        if not versions:
            return None
        target = self._safe_target(path)
        if must_exist and directory and not target.is_dir():
            raise NotFoundError("Lifecycle artifact must be an existing directory.")
        if must_exist and not directory and not target.is_file():
            raise NotFoundError("Lifecycle artifact must be an existing file.")
        locator = target.relative_to(self.artifacts_dir).as_posix()
        return self._register(
            team_id=team_id,
            artifact_kind=artifact_kind,
            locator_kind="directory" if directory else "file",
            locator=locator,
            acl_versions=versions,
        )

    def register_requirement_case(
        self,
        *,
        team_id: str,
        case_id: str,
        access: ResourceAccess | None = None,
        acl_versions: set[str] | None = None,
    ) -> ArtifactLineageRecord | None:
        versions = set(acl_versions or set())
        if access is not None:
            versions.update(access.acl_versions())
        if not versions:
            return None
        return self._register(
            team_id=team_id,
            artifact_kind="requirement_case",
            locator_kind="requirement_case",
            locator=case_id,
            acl_versions=versions,
        )

    def purge(
        self,
        *,
        team_id: str,
        acl_versions: set[str],
        reason: str,
        delete_requirement_case: Callable[[str], None] | None = None,
    ) -> ArtifactPurgeReport:
        requested_versions = {value.strip() for value in acl_versions if value.strip()}
        report = ArtifactPurgeReport(team_id=team_id, acl_versions=requested_versions)
        if not requested_versions:
            return report

        with _LINEAGE_LOCK:
            ledger = self.load()
            updated_records: list[ArtifactLineageRecord] = []
            for record in ledger.records:
                if (
                    record.team_id != team_id
                    or record.status == "purged"
                    or not (record.acl_versions & requested_versions)
                ):
                    updated_records.append(record)
                    continue
                item, updated = self._purge_record(
                    record,
                    reason=reason,
                    delete_requirement_case=delete_requirement_case,
                )
                report.items.append(item)
                updated_records.append(updated)
            ledger.records = updated_records
            self._save(ledger)

        failures = [item for item in report.items if item.status == "cleanup_failed"]
        report.cleanup_complete = not failures
        report.warnings = [
            f"Artifact cleanup failed for {item.artifact_id}: {item.error}" for item in failures
        ]
        return report

    def load(self) -> ArtifactLineageLedger:
        if not self.path.exists():
            return ArtifactLineageLedger()
        try:
            return ArtifactLineageLedger.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DreamError("Artifact lineage ledger is unreadable or invalid.") from exc

    def _register(
        self,
        *,
        team_id: str,
        artifact_kind: str,
        locator_kind: str,
        locator: str,
        acl_versions: set[str],
    ) -> ArtifactLineageRecord:
        identity = json.dumps(
            [artifact_kind, team_id, locator_kind, locator],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        artifact_id = f"artifact:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"
        record = ArtifactLineageRecord(
            artifact_id=artifact_id,
            team_id=team_id,
            artifact_kind=artifact_kind,
            locator_kind=locator_kind,
            locator=locator,
            acl_versions=acl_versions,
            status="active",
            registered_at=_now(),
        )
        with _LINEAGE_LOCK:
            ledger = self.load()
            ledger.records = [item for item in ledger.records if item.artifact_id != artifact_id]
            ledger.records.append(record)
            ledger.records.sort(key=lambda item: item.artifact_id)
            self._save(ledger)
        return record

    def _purge_record(
        self,
        record: ArtifactLineageRecord,
        *,
        reason: str,
        delete_requirement_case: Callable[[str], None] | None,
    ) -> tuple[ArtifactPurgeItem, ArtifactLineageRecord]:
        try:
            existed = True
            if record.locator_kind == "requirement_case":
                if delete_requirement_case is None:
                    raise DreamError("Requirement Case cleanup handler is not configured.")
                delete_requirement_case(record.locator)
            else:
                target = self._safe_target(self.artifacts_dir / record.locator)
                existed = target.exists()
                if target.is_dir():
                    if record.locator_kind != "directory":
                        raise DreamError(
                            "Lineage locator expected a file but resolved to a directory."
                        )
                    shutil.rmtree(target)
                elif target.exists():
                    if record.locator_kind != "file":
                        raise DreamError(
                            "Lineage locator expected a directory but resolved to a file."
                        )
                    target.unlink()
            status = "purged" if existed else "already_absent"
            return (
                ArtifactPurgeItem(artifact_id=record.artifact_id, status=status),
                record.model_copy(
                    update={
                        "status": "purged",
                        "purged_at": _now(),
                        "purge_reason": reason,
                        "cleanup_error": None,
                    }
                ),
            )
        except (DreamError, OSError, ValueError) as exc:
            error = str(exc)
            return (
                ArtifactPurgeItem(
                    artifact_id=record.artifact_id,
                    status="cleanup_failed",
                    error=error,
                ),
                record.model_copy(update={"status": "cleanup_failed", "cleanup_error": error}),
            )

    def _safe_target(self, path: Path) -> Path:
        target = path.resolve()
        if target == self.artifacts_dir or not target.is_relative_to(self.artifacts_dir):
            raise PathTraversalError("Lifecycle artifact must stay below the artifact root.")
        control_root = (self.artifacts_dir / "pilot-security").resolve()
        if target == control_root or target.is_relative_to(control_root):
            raise PathTraversalError("Lifecycle control-plane artifacts cannot be registered.")
        return target

    def _save(self, ledger: ArtifactLineageLedger) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(ledger.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
