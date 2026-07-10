# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import ValidationError

from dream.audit.repository import AuditRepository
from dream.config import resolve_config
from dream.connectors.lineage import ArtifactLineageRegistry
from dream.connectors.repository import ConnectorLifecycleRepository
from dream.core.errors import DreamError, PathTraversalError
from dream.core.paths import get_artifacts_dir, get_audit_db_path
from dream.dlp.repository import DlpEventRepository
from dream.evals.models import EvaluationScorecard
from dream.evals.repository import EvaluationRepository
from dream.llm.egress import ProviderEgressRepository
from dream.pilot_evidence.models import (
    EvidenceCoverage,
    EvidenceFileChecksum,
    EvidenceSection,
    PilotEvidenceBuildResult,
    PilotEvidenceManifest,
    PilotEvidenceVerificationReport,
)
from dream.security.revocation import AccessRevocationRegistry

SECTION_FILES: dict[str, str] = {
    "audit_runs": "audit-runs.json",
    "human_ratings": "human-ratings.json",
    "evaluations": "evaluations.json",
    "access_revocations": "access-revocations.json",
    "connector_lifecycle": "connector-lifecycle.json",
    "artifact_lineage": "artifact-lineage.json",
    "dlp_decisions": "dlp-decisions.json",
    "provider_egress": "provider-egress.json",
}
KNOWN_COVERAGE_GAPS = [
    "runtime_identity_decisions_not_persisted",
    "access_policy_decisions_not_persisted",
]
SAFE_RECORD_STRINGS = {
    "source_state",
    "lifecycle_event",
    "activated",
    "unchanged",
    "replaced",
    "reactivated",
    "deleted",
    "cleanup_retry",
    "active",
    "purged",
    "cleanup_failed",
    "file",
    "directory",
    "requirement_case",
    "pre_index",
    "pre_prompt",
    "pre_persist",
    "post_response",
    "allowed",
    "blocked",
    "public_demo",
    "internal",
    "sensitive",
    "local_demo",
    "source_acl",
    "unscoped",
    "_other",
    "private_key",
    "prompt_injection",
    "secret_assignment",
    "aws_access_key",
    "jwt",
    "us_ssn",
    "email_address",
    "blocked_classification",
    "oversize_content",
    "medium",
    "high",
    "critical",
    "redact",
    "block",
    "completed",
    "failed",
    "local_provider_no_egress",
    "private_plugin_provider_not_attested",
    "unsupported_private_provider",
    "provider_identity_incomplete",
    "provider_endpoint_invalid",
    "approval_endpoint_invalid",
    "approval_not_yet_valid",
    "approval_expired",
    "approval_identity_mismatch",
    "approval_file_not_configured",
    "approval_file_path_not_absolute",
    "approval_file_inside_public_checkout",
    "approval_file_invalid",
    "exact_approval_match",
    "response_identity_mismatch",
    "runtime_provider_identity_mismatch",
}
SAFE_RECORD_KEYS = {
    "access",
    "acl_scope",
    "acl_version_hashes",
    "action",
    "actor_hash",
    "allowed_group_count",
    "allowed_principal_count",
    "approval_id_hash",
    "artifact_id_hash",
    "artifact_kind_hash",
    "base_url_fingerprint_hash",
    "block_count",
    "case_id_hash",
    "category",
    "category_hash",
    "classification",
    "cleanup_complete",
    "cleanup_error_hash",
    "comment_char_count",
    "comment_hash",
    "confidence",
    "connector_id_hash",
    "content_fingerprint_hash",
    "correctness_score",
    "created_at",
    "current_source_version_hash",
    "deleted_at",
    "deleted_by_hash",
    "deletion_reason_hash",
    "dimensions",
    "duration_ms",
    "evaluation_id_hash",
    "event_count",
    "event_id_hash",
    "evidence_count",
    "findings",
    "fingerprint_hash",
    "first_seen_at",
    "grade_hash",
    "hallucination_warning_count",
    "input_char_count",
    "input_fingerprint_hash",
    "last_seen_at",
    "llm_judge",
    "locator_hash",
    "locator_kind",
    "manifest_fingerprint_hash",
    "missing_critical_item_count",
    "missing_evidence_count",
    "missing_item_count",
    "model_hash",
    "model_name_hash",
    "model_provider_hash",
    "name_hash",
    "occurred_at",
    "occurrences",
    "output_char_count",
    "output_fingerprint_hash",
    "output_path_hash",
    "overall_score",
    "pass_status_hash",
    "passed",
    "policy_version_hash",
    "previous_source_version_hash",
    "prompt_version_hash",
    "provider_hash",
    "purge_reason_hash",
    "purged_artifact_id_hashes",
    "purged_at",
    "raw_response_included",
    "readiness_hash",
    "reason_hash",
    "reason_code",
    "reason_code_hash",
    "recommendation_count",
    "record_type",
    "redaction_count",
    "registered_at",
    "repo_name_hash",
    "resource_id_fingerprint_hash",
    "retrieved_source_count",
    "retrieved_source_hashes",
    "revoked_acl_version_hashes",
    "revoked_at",
    "revoked_by_hash",
    "risk_count",
    "rule_id_hash",
    "run_id_hash",
    "score",
    "severity",
    "source_acl_lineage_hashes",
    "source_acl_version_hash",
    "source_coverage_field_count",
    "source_coverage_true_count",
    "source_id_hash",
    "source_key_hash",
    "source_type_hash",
    "source_version_hash",
    "stage",
    "status",
    "status_hash",
    "target_id_hash",
    "target_type_hash",
    "timestamp",
    "token_usage_field_count",
    "token_usage_total",
    "use_case_hash",
    "usefulness_score",
    "warning_count",
    "warning_hash",
    "warning_hashes",
    "weight",
}


class PilotEvidenceExporter:
    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        audit_db_path: Path | None = None,
        mode: Literal["public-demo", "private-extension"] | None = None,
    ) -> None:
        self.artifacts_dir = (artifacts_dir or get_artifacts_dir()).resolve()
        self.audit_db_path = (audit_db_path or get_audit_db_path()).resolve()
        self.mode = mode or resolve_config().mode

    def build(
        self,
        *,
        team_id: str,
        confirm_team: str,
        operator_id: str,
        reason: str,
        output_root: Path | None = None,
    ) -> PilotEvidenceBuildResult:
        team = _required(team_id, "team_id")
        if confirm_team != team:
            raise DreamError("Evidence export confirmation must exactly match team_id.")
        operator = _required(operator_id, "operator_id")
        export_reason = _required(reason, "reason")
        root = self._safe_output_root(output_root or self.artifacts_dir / "pilot-evidence")
        generated_at = datetime.now(UTC).isoformat()
        resolved_bundle_id = (
            f"pilot-evidence-{_hash_text(team)[:12]}-"
            f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
        )
        bundle_dir = root / resolved_bundle_id
        if bundle_dir.exists():
            raise DreamError("Evidence bundle directory already exists; bundles are immutable.")
        bundle_dir.mkdir(parents=True)
        try:
            sections, coverage = self._collect(team)
            checksums: list[EvidenceFileChecksum] = []
            for source, filename in SECTION_FILES.items():
                section = sections[source]
                path = bundle_dir / filename
                _write_json(path, section.model_dump(mode="json"))
                checksums.append(_checksum(path, bundle_dir))
            manifest = PilotEvidenceManifest(
                bundle_id=resolved_bundle_id,
                generated_at=generated_at,
                mode=self.mode,
                team_id_hash=_hash_text(team),
                operator_id_hash=_hash_text(operator),
                reason_hash=_hash_text(export_reason),
                known_coverage_gaps=KNOWN_COVERAGE_GAPS,
                coverage=sorted(coverage, key=lambda item: item.source),
                files=sorted(checksums, key=lambda item: item.path),
            )
            manifest.bundle_root_sha256 = _manifest_root(manifest)
            manifest_path = bundle_dir / "manifest.json"
            _write_json(manifest_path, manifest.model_dump(mode="json"))
            return PilotEvidenceBuildResult(
                bundle_id=manifest.bundle_id,
                bundle_dir=bundle_dir.as_posix(),
                manifest_path=manifest_path.as_posix(),
                manifest_sha256=_hash_file(manifest_path),
                bundle_root_sha256=manifest.bundle_root_sha256,
                status=manifest.status,
                known_coverage_gaps=manifest.known_coverage_gaps,
            )
        except Exception:
            _remove_partial_bundle(bundle_dir)
            raise

    def _collect(
        self,
        team_id: str,
    ) -> tuple[dict[str, EvidenceSection], list[EvidenceCoverage]]:
        sections: dict[str, EvidenceSection] = {}
        coverage: list[EvidenceCoverage] = []

        sqlite_sections, sqlite_hash = self._read_sqlite_snapshot(team_id)
        for source, records in sqlite_sections.items():
            sections[source] = EvidenceSection(source=source, scope="team", records=records)
            coverage.append(
                _coverage(
                    source,
                    "team",
                    records,
                    sqlite_hash,
                    source_exists=self.audit_db_path.exists(),
                )
            )

        revocations, revocation_hash, exists = _stable_load(
            AccessRevocationRegistry(
                self.artifacts_dir / "pilot-security/access-revocations.json"
            ).path,
            lambda: AccessRevocationRegistry(
                self.artifacts_dir / "pilot-security/access-revocations.json"
            ).load(),
        )
        revocation_records = [
            {
                "source_acl_version_hash": _hash_text(item.source_acl_version),
                "revoked_at": _safe_timestamp(item.revoked_at),
                "revoked_by_hash": _hash_text(item.revoked_by),
                "reason_hash": _hash_text(item.reason),
            }
            for item in revocations.events
            if item.team_id == team_id
        ]
        sections["access_revocations"] = EvidenceSection(
            source="access_revocations", scope="team", records=revocation_records
        )
        coverage.append(
            _coverage(
                "access_revocations",
                "team",
                revocation_records,
                revocation_hash,
                source_exists=exists,
            )
        )

        connector_repo = ConnectorLifecycleRepository(self.artifacts_dir)
        connector, connector_hash, exists = _stable_load(
            connector_repo.path,
            connector_repo.load,
        )
        connector_records = self._connector_records(connector, team_id)
        sections["connector_lifecycle"] = EvidenceSection(
            source="connector_lifecycle", scope="team", records=connector_records
        )
        coverage.append(
            _coverage(
                "connector_lifecycle",
                "team",
                connector_records,
                connector_hash,
                source_exists=exists,
            )
        )

        lineage_repo = ArtifactLineageRegistry(self.artifacts_dir)
        lineage, lineage_hash, exists = _stable_load(lineage_repo.path, lineage_repo.load)
        lineage_records = [
            {
                "artifact_id_hash": _hash_text(item.artifact_id),
                "artifact_kind_hash": _hash_text(item.artifact_kind),
                "locator_kind": item.locator_kind,
                "locator_hash": _hash_text(item.locator),
                "acl_version_hashes": _hash_values(item.acl_versions),
                "status": item.status,
                "registered_at": _safe_timestamp(item.registered_at),
                "purged_at": _safe_optional_timestamp(item.purged_at),
                "purge_reason_hash": _hash_optional(item.purge_reason),
                "cleanup_error_hash": _hash_optional(item.cleanup_error),
            }
            for item in lineage.records
            if item.team_id == team_id
        ]
        sections["artifact_lineage"] = EvidenceSection(
            source="artifact_lineage", scope="team", records=lineage_records
        )
        coverage.append(
            _coverage(
                "artifact_lineage",
                "team",
                lineage_records,
                lineage_hash,
                source_exists=exists,
            )
        )

        dlp_repo = DlpEventRepository(self.artifacts_dir)
        dlp, dlp_hash, exists = _stable_load(dlp_repo.path, dlp_repo.load)
        dlp_records = [_dlp_record(item) for item in dlp.events if item.team_id == team_id]
        sections["dlp_decisions"] = EvidenceSection(
            source="dlp_decisions", scope="team", records=dlp_records
        )
        coverage.append(
            _coverage(
                "dlp_decisions",
                "team",
                dlp_records,
                dlp_hash,
                source_exists=exists,
            )
        )

        provider_repo = ProviderEgressRepository(self.artifacts_dir)
        provider, provider_hash, exists = _stable_load(
            provider_repo.path,
            provider_repo.load,
        )
        provider_records = _aggregate_provider_events(provider)
        sections["provider_egress"] = EvidenceSection(
            source="provider_egress", scope="deployment", records=provider_records
        )
        coverage.append(
            _coverage(
                "provider_egress",
                "deployment",
                provider_records,
                provider_hash,
                source_exists=exists,
            )
        )
        return sections, coverage

    def _read_sqlite_snapshot(
        self,
        team_id: str,
    ) -> tuple[dict[str, list[dict[str, object]]], str]:
        AuditRepository(self.audit_db_path)
        EvaluationRepository(self.audit_db_path)
        conn = sqlite3.connect(self.audit_db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN")
            audit_rows = conn.execute(
                """
                SELECT run_id, timestamp, use_case, case_id, repo_name, input_hash,
                       retrieved_source_paths, model_provider, model_name, output_path,
                       status, warnings
                FROM audit_runs
                WHERE team_id = ?
                ORDER BY timestamp, run_id
                """,
                (team_id,),
            ).fetchall()
            rating_rows = conn.execute(
                """
                SELECT h.run_id, h.usefulness_score, h.correctness_score,
                       h.comments, h.created_at
                FROM human_ratings h
                INNER JOIN audit_runs a ON a.run_id = h.run_id
                WHERE a.team_id = ?
                ORDER BY h.created_at, h.id
                """,
                (team_id,),
            ).fetchall()
            evaluation_rows = conn.execute(
                """
                SELECT payload
                FROM evaluation_scorecards
                WHERE team_id = ?
                ORDER BY created_at, evaluation_id
                """,
                (team_id,),
            ).fetchall()
            raw_snapshot = {
                "audit": [dict(row) for row in audit_rows],
                "ratings": [dict(row) for row in rating_rows],
                "evaluations": [dict(row) for row in evaluation_rows],
            }
        except sqlite3.Error as exc:
            raise DreamError("Pilot evidence SQLite source could not be read.") from exc
        finally:
            conn.close()
        audit_records = [self._audit_record(row) for row in audit_rows]
        rating_records = [self._rating_record(row) for row in rating_rows]
        try:
            evaluation_records = [
                self._evaluation_record(
                    EvaluationScorecard.model_validate_json(row["payload"])
                )
                for row in evaluation_rows
            ]
        except (ValidationError, ValueError, TypeError) as exc:
            raise DreamError(
                "Pilot evidence evaluation source is unreadable or invalid."
            ) from exc
        return (
            {
                "audit_runs": audit_records,
                "human_ratings": rating_records,
                "evaluations": evaluation_records,
            },
            _hash_json(raw_snapshot),
        )

    @staticmethod
    def _audit_record(row: sqlite3.Row) -> dict[str, object]:
        sources = _json_string_list(row["retrieved_source_paths"])
        warnings = _json_string_list(row["warnings"])
        return {
            "run_id_hash": _hash_text(row["run_id"]),
            "timestamp": _safe_timestamp(row["timestamp"]),
            "use_case_hash": _hash_text(row["use_case"]),
            "case_id_hash": _hash_optional(row["case_id"]),
            "repo_name_hash": _hash_optional(row["repo_name"]),
            "input_fingerprint_hash": _hash_text(row["input_hash"]),
            "retrieved_source_count": len(sources),
            "retrieved_source_hashes": _hash_values(sources),
            "model_provider_hash": _hash_text(row["model_provider"]),
            "model_name_hash": _hash_text(row["model_name"]),
            "output_path_hash": _hash_text(row["output_path"]),
            "status_hash": _hash_text(row["status"]),
            "warning_count": len(warnings),
            "warning_hashes": _hash_values(warnings),
        }

    @staticmethod
    def _rating_record(row: sqlite3.Row) -> dict[str, object]:
        comments = str(row["comments"])
        return {
            "run_id_hash": _hash_text(row["run_id"]),
            "usefulness_score": row["usefulness_score"],
            "correctness_score": row["correctness_score"],
            "comment_hash": _hash_text(comments),
            "comment_char_count": len(comments),
            "created_at": _safe_timestamp(row["created_at"]),
        }

    @staticmethod
    def _evaluation_record(scorecard: EvaluationScorecard) -> dict[str, object]:
        judge = scorecard.llm_judge
        return {
            "evaluation_id_hash": _hash_text(scorecard.evaluation_id),
            "target_type_hash": _hash_text(scorecard.target_type),
            "target_id_hash": _hash_optional(scorecard.target_id),
            "run_id_hash": _hash_optional(scorecard.run_id),
            "case_id_hash": _hash_optional(scorecard.case_id),
            "repo_name_hash": _hash_optional(scorecard.repo_name),
            "created_at": _safe_timestamp(scorecard.created_at),
            "overall_score": scorecard.overall_score,
            "grade_hash": _hash_text(scorecard.grade),
            "pass_status_hash": _hash_text(scorecard.pass_status),
            "dimensions": [
                {
                    "name_hash": _hash_text(item.name),
                    "score": item.score,
                    "weight": item.weight,
                    "passed": item.passed,
                    "evidence_count": len(item.evidence),
                    "missing_item_count": len(item.missing_items),
                    "recommendation_count": len(item.recommendations),
                }
                for item in scorecard.dimensions
            ],
            "missing_critical_item_count": len(scorecard.missing_critical_items),
            "hallucination_warning_count": len(scorecard.hallucination_warnings),
            "source_coverage_field_count": len(scorecard.source_coverage),
            "source_coverage_true_count": sum(scorecard.source_coverage.values()),
            "recommendation_count": len(scorecard.recommendations),
            "llm_judge": (
                {
                    "status": judge.status,
                    "provider_hash": _hash_optional(judge.provider),
                    "model_hash": _hash_optional(judge.model),
                    "prompt_version_hash": _hash_text(judge.prompt_version),
                    "input_fingerprint_hash": _hash_optional(judge.input_hash),
                    "duration_ms": judge.duration_ms,
                    "readiness_hash": _hash_optional(judge.readiness),
                    "confidence": judge.confidence,
                    "risk_count": len(judge.risks),
                    "missing_evidence_count": len(judge.missing_evidence),
                    "recommendation_count": len(judge.recommendations),
                    "token_usage_field_count": len(judge.token_usage or {}),
                    "token_usage_total": sum(
                        value
                        for value in (judge.token_usage or {}).values()
                        if isinstance(value, int) and not isinstance(value, bool)
                    ),
                    "warning_hash": _hash_optional(judge.warning),
                    "raw_response_included": False,
                }
                if judge
                else None
            ),
            "warning_count": len(scorecard.warnings),
            "warning_hashes": _hash_values(scorecard.warnings),
        }

    @staticmethod
    def _connector_records(ledger, team_id: str) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for item in ledger.states:
            if item.team_id != team_id:
                continue
            records.append(
                {
                    "record_type": "source_state",
                    "source_key_hash": _hash_text(item.source_key),
                    "connector_id_hash": _hash_text(item.connector_id),
                    "source_id_hash": _hash_text(item.source_id),
                    "source_type_hash": _hash_text(item.source_type),
                    "source_version_hash": _hash_text(item.source_version),
                    "content_fingerprint_hash": _hash_text(item.content_hash),
                    "access": _access_summary(item.access),
                    "status": item.status,
                    "first_seen_at": _safe_timestamp(item.first_seen_at),
                    "last_seen_at": _safe_timestamp(item.last_seen_at),
                    "deleted_at": _safe_optional_timestamp(item.deleted_at),
                    "deleted_by_hash": _hash_optional(item.deleted_by),
                    "deletion_reason_hash": _hash_optional(item.deletion_reason),
                }
            )
        for item in ledger.events:
            if item.team_id != team_id:
                continue
            records.append(
                {
                    "record_type": "lifecycle_event",
                    "event_id_hash": _hash_text(item.event_id),
                    "source_key_hash": _hash_text(item.source_key),
                    "action": item.action,
                    "actor_hash": _hash_text(item.actor),
                    "occurred_at": _safe_timestamp(item.occurred_at),
                    "previous_source_version_hash": _hash_optional(
                        item.previous_source_version
                    ),
                    "current_source_version_hash": _hash_optional(
                        item.current_source_version
                    ),
                    "revoked_acl_version_hashes": _hash_values(
                        item.revoked_acl_versions
                    ),
                    "purged_artifact_id_hashes": _hash_values(
                        item.purged_artifact_ids
                    ),
                    "cleanup_complete": item.cleanup_complete,
                    "warning_count": len(item.warnings),
                    "warning_hashes": _hash_values(item.warnings),
                }
            )
        return sorted(records, key=lambda item: json.dumps(item, sort_keys=True))

    def _safe_output_root(self, output_root: Path) -> Path:
        resolved = output_root.resolve()
        if not resolved.is_relative_to(self.artifacts_dir):
            raise PathTraversalError("Evidence output must stay inside the artifact root.")
        control_root = (self.artifacts_dir / "pilot-security").resolve()
        if resolved == control_root or resolved.is_relative_to(control_root):
            raise PathTraversalError("Evidence output cannot enter the security control plane.")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved


class PilotEvidenceVerifier:
    def verify(
        self,
        bundle_dir: Path,
        *,
        expected_root_sha256: str | None = None,
    ) -> PilotEvidenceVerificationReport:
        verified_at = datetime.now(UTC).isoformat()
        failures: list[str] = []
        checks: dict[str, bool] = {}
        root = bundle_dir.resolve()
        manifest_path = root / "manifest.json"
        if bundle_dir.is_symlink() or not root.is_dir() or manifest_path.is_symlink():
            return _verification_failure(verified_at, "bundle_path_invalid")
        try:
            manifest = PilotEvidenceManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, ValueError):
            return _verification_failure(verified_at, "manifest_invalid")

        expected_names = {"manifest.json", *SECTION_FILES.values()}
        actual_names = {path.name for path in root.iterdir()}
        checks["exact_file_set"] = actual_names == expected_names
        if not checks["exact_file_set"]:
            failures.append("exact_file_set")
        checks["manifest_file_contract"] = {
            item.path for item in manifest.files
        } == set(SECTION_FILES.values()) and len(manifest.files) == len(SECTION_FILES)
        if not checks["manifest_file_contract"]:
            failures.append("manifest_file_contract")
        checks["coverage_contract"] = {
            item.source for item in manifest.coverage
        } == set(SECTION_FILES) and len(manifest.coverage) == len(SECTION_FILES)
        if not checks["coverage_contract"]:
            failures.append("coverage_contract")
        checks["known_gaps_contract"] = (
            manifest.known_coverage_gaps == KNOWN_COVERAGE_GAPS
        )
        if not checks["known_gaps_contract"]:
            failures.append("known_gaps_contract")
        checks["bundle_id_contract"] = manifest.bundle_id.startswith(
            f"pilot-evidence-{manifest.team_id_hash[:12]}-"
        )
        if not checks["bundle_id_contract"]:
            failures.append("bundle_id_contract")

        coverage_by_source = {item.source: item for item in manifest.coverage}
        for item in manifest.files:
            safe_name = Path(item.path).name == item.path and "/" not in item.path
            path = root / item.path
            file_ok = (
                safe_name
                and not path.is_symlink()
                and path.is_file()
                and _checksum_matches(path, root, item)
            )
            checks[f"file:{item.path}"] = file_ok
            if not file_ok:
                failures.append(f"file:{item.path}")
                continue
            try:
                section = EvidenceSection.model_validate_json(path.read_text(encoding="utf-8"))
                coverage_item = coverage_by_source.get(section.source)
                expected_status_ok = (
                    coverage_item is not None
                    and (
                        coverage_item.status == "included"
                        if section.records
                        else coverage_item.status in {"empty", "missing"}
                    )
                )
                snapshot_contract_ok = (
                    coverage_item is not None
                    and (
                        coverage_item.source_snapshot_sha256 is None
                        if coverage_item.status == "missing"
                        else coverage_item.source_snapshot_sha256 is not None
                    )
                )
                section_ok = (
                    SECTION_FILES.get(section.source) == item.path
                    and coverage_item is not None
                    and coverage_item.scope == section.scope
                    and coverage_item.record_count == len(section.records)
                    and expected_status_ok
                    and snapshot_contract_ok
                    and all(_record_values_safe(record) for record in section.records)
                )
            except (OSError, ValidationError, ValueError):
                section_ok = False
            checks[f"section:{item.path}"] = section_ok
            if not section_ok:
                failures.append(f"section:{item.path}")

        calculated_root = _manifest_root(manifest)
        checks["bundle_root"] = calculated_root == manifest.bundle_root_sha256
        if not checks["bundle_root"]:
            failures.append("bundle_root")
        expected_matched = None
        if expected_root_sha256 is not None:
            expected_matched = expected_root_sha256 == manifest.bundle_root_sha256
            checks["expected_root"] = expected_matched
            if not expected_matched:
                failures.append("expected_root")
        return PilotEvidenceVerificationReport(
            verified_at=verified_at,
            passed=not failures,
            bundle_id=manifest.bundle_id,
            bundle_root_sha256=manifest.bundle_root_sha256,
            expected_root_matched=expected_matched,
            checks=checks,
            failures=list(dict.fromkeys(failures)),
        )


def _aggregate_provider_events(events) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[str]] = defaultdict(list)
    for item in events:
        key = (
            item.status,
            item.reason_code,
            item.provider,
            item.model,
            item.base_url_hash,
            item.approval_id,
            item.manifest_hash,
        )
        groups[key].append(_safe_timestamp(item.timestamp))
    records = []
    for key, timestamps in groups.items():
        status, reason, provider, model, base_url_hash, approval_id, manifest_hash = key
        records.append(
            {
                "status": status,
                "reason_code": _known_provider_reason(str(reason)),
                "reason_code_hash": _hash_text(str(reason)),
                "provider_hash": _hash_text(str(provider)),
                "model_hash": _hash_optional(model),
                "base_url_fingerprint_hash": _hash_optional(base_url_hash),
                "approval_id_hash": _hash_optional(approval_id),
                "manifest_fingerprint_hash": _hash_optional(manifest_hash),
                "event_count": len(timestamps),
                "first_seen_at": min(timestamps),
                "last_seen_at": max(timestamps),
            }
        )
    return sorted(records, key=lambda item: json.dumps(item, sort_keys=True))


def _dlp_record(item) -> dict[str, object]:
    allowed_classifications = {"public_demo", "internal", "sensitive", "blocked"}
    allowed_categories = {
        "private_key",
        "prompt_injection",
        "secret_assignment",
        "aws_access_key",
        "jwt",
        "us_ssn",
        "email_address",
        "blocked_classification",
        "oversize_content",
    }
    classification = (
        item.classification if item.classification in allowed_classifications else "_other"
    )
    return {
        "event_id_hash": _hash_text(item.event_id),
        "timestamp": _safe_timestamp(item.timestamp),
        "policy_version_hash": _hash_text(item.policy_version),
        "stage": item.stage,
        "status": item.status,
        "classification": classification,
        "resource_id_fingerprint_hash": _hash_text(item.resource_id_hash),
        "input_fingerprint_hash": _hash_text(item.input_hash),
        "output_fingerprint_hash": _hash_text(item.output_hash),
        "input_char_count": item.input_char_count,
        "output_char_count": item.output_char_count,
        "redaction_count": item.redaction_count,
        "block_count": item.block_count,
        "findings": [
            {
                "rule_id_hash": _hash_text(finding.rule_id),
                "category": (
                    finding.category
                    if finding.category in allowed_categories
                    else "_other"
                ),
                "category_hash": _hash_text(finding.category),
                "severity": finding.severity,
                "action": finding.action,
                "fingerprint_hash": _hash_text(finding.fingerprint),
                "occurrences": finding.occurrences,
            }
            for finding in item.findings
        ],
    }


def _known_provider_reason(value: str) -> str:
    known = {
        "local_provider_no_egress",
        "private_plugin_provider_not_attested",
        "unsupported_private_provider",
        "provider_identity_incomplete",
        "provider_endpoint_invalid",
        "approval_endpoint_invalid",
        "approval_not_yet_valid",
        "approval_expired",
        "approval_identity_mismatch",
        "approval_file_not_configured",
        "approval_file_path_not_absolute",
        "approval_file_inside_public_checkout",
        "approval_file_invalid",
        "exact_approval_match",
        "response_identity_mismatch",
        "runtime_provider_identity_mismatch",
    }
    return value if value in known else "_other"


def _access_summary(access) -> dict[str, object]:
    return {
        "classification": access.classification,
        "acl_scope": access.acl_scope,
        "allowed_principal_count": len(access.allowed_principal_ids),
        "allowed_group_count": len(access.allowed_group_ids),
        "source_acl_version_hash": _hash_optional(access.source_acl_version),
        "source_acl_lineage_hashes": _hash_values(access.source_acl_lineage),
    }


def _coverage(
    source: str,
    scope: Literal["team", "deployment"],
    records: list[dict[str, object]],
    snapshot_hash: str | None,
    *,
    source_exists: bool,
) -> EvidenceCoverage:
    status = "included" if records else "empty" if source_exists else "missing"
    return EvidenceCoverage(
        source=source,
        scope=scope,
        status=status,
        record_count=len(records),
        source_snapshot_sha256=snapshot_hash,
    )


def _stable_load(path: Path, loader: Callable[[], Any]) -> tuple[Any, str | None, bool]:
    existed_before = path.is_file()
    before = _hash_file(path) if existed_before else None
    value = loader()
    existed_after = path.is_file()
    after = _hash_file(path) if existed_after else None
    if existed_before != existed_after or before != after:
        raise DreamError(f"Evidence source changed during export: {path.name}")
    return value, after, existed_after


def _json_string_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DreamError("Audit JSON metadata is invalid.") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise DreamError("Audit JSON metadata must be a string list.")
    return parsed


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _checksum(path: Path, root: Path) -> EvidenceFileChecksum:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise PathTraversalError("Evidence file escaped the bundle directory.")
    return EvidenceFileChecksum(
        path=resolved.relative_to(root.resolve()).as_posix(),
        sha256=_hash_file(resolved),
        size_bytes=resolved.stat().st_size,
    )


def _checksum_matches(path: Path, root: Path, expected: EvidenceFileChecksum) -> bool:
    try:
        actual = _checksum(path, root)
    except (OSError, DreamError):
        return False
    return actual.sha256 == expected.sha256 and actual.size_bytes == expected.size_bytes


def _manifest_root(manifest: PilotEvidenceManifest) -> str:
    payload = manifest.model_dump(mode="json", exclude={"bundle_root_sha256"})
    return _hash_json(payload)


def _hash_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_optional(value: object | None) -> str | None:
    return _hash_text(str(value)) if value is not None else None


def _hash_values(values) -> list[str]:
    return sorted({_hash_text(str(item)) for item in values})


def _safe_timestamp(value: object) -> str:
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DreamError("Evidence source contains an invalid timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DreamError("Evidence source timestamp must include a timezone.")
    return parsed.astimezone(UTC).isoformat()


def _safe_optional_timestamp(value: object | None) -> str | None:
    return _safe_timestamp(value) if value is not None else None


def _record_values_safe(value: object) -> bool:
    if value is None or isinstance(value, bool | int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        if value in SAFE_RECORD_STRINGS:
            return True
        if len(value) == 64 and all(char in "0123456789abcdef" for char in value):
            return True
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    if isinstance(value, list):
        return all(_record_values_safe(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and key in SAFE_RECORD_KEYS
            and _record_values_safe(item)
            for key, item in value.items()
        )
    return False


def _required(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DreamError(f"Evidence export {label} is required.")
    return normalized


def _remove_partial_bundle(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file() and not child.is_symlink():
            child.unlink()
    path.rmdir()


def _verification_failure(
    verified_at: str,
    failure: str,
) -> PilotEvidenceVerificationReport:
    return PilotEvidenceVerificationReport(
        verified_at=verified_at,
        passed=False,
        checks={failure: False},
        failures=[failure],
    )
