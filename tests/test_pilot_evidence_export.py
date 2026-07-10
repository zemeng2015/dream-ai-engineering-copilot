# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dream.audit.models import AuditRecord
from dream.audit.repository import AuditRepository
from dream.cli.main import app
from dream.connectors.lineage import ArtifactLineageRegistry
from dream.connectors.models import ConnectorLifecycleEvent, ConnectorSourceState
from dream.connectors.repository import ConnectorLifecycleRepository
from dream.core.errors import DreamError, PathTraversalError
from dream.dlp.models import DlpDecisionEvidence, DlpFindingEvidence
from dream.dlp.repository import DlpEventRepository
from dream.evals.models import (
    EvaluationDimension,
    EvaluationScorecard,
    HumanRating,
    LLMJudgeResult,
)
from dream.evals.repository import EvaluationRepository
from dream.llm.egress import ProviderEgressEvidence, ProviderEgressRepository
from dream.pilot_evidence import PilotEvidenceExporter, PilotEvidenceVerifier
from dream.security.models import ResourceAccess
from dream.security.revocation import AccessRevocationRegistry

SECRET = "ultra-private-value"
TEAM = "team-alpha-secret"
OTHER_TEAM = "team-beta-secret"
NOW = datetime.now(UTC).isoformat()


def _seed_evidence(artifacts: Path, db_path: Path) -> None:
    audit = AuditRepository(db_path)
    audit.add_audit_record(
        AuditRecord(
            run_id=f"run-{SECRET}",
            timestamp=NOW,
            use_case=f"use-case-{SECRET}",
            team_id=TEAM,
            case_id=f"case-{SECRET}",
            repo_name=f"repo-{SECRET}",
            input_hash=f"input-{SECRET}",
            retrieved_source_paths=[f"private/{SECRET}/runbook.md"],
            model_provider=f"provider-{SECRET}",
            model_name=f"model-{SECRET}",
            output_path=f"private/{SECRET}/output.md",
            status=f"status-{SECRET}",
            warnings=[f"warning-{SECRET}"],
        )
    )
    audit.add_audit_record(
        AuditRecord(
            run_id="other-run",
            timestamp=NOW,
            use_case="other-use-case",
            team_id=OTHER_TEAM,
            input_hash="other-input",
            retrieved_source_paths=["other-team-source"],
            model_provider="other-provider",
            model_name="other-model",
            output_path="other-output",
            status="success",
            warnings=[],
        )
    )
    audit.add_rating(
        HumanRating(
            run_id=f"run-{SECRET}",
            usefulness_score=4,
            correctness_score=5,
            comments=f"rating-comment-{SECRET}",
            created_at=NOW,
        )
    )

    EvaluationRepository(db_path).save(
        EvaluationScorecard(
            evaluation_id=f"eval-{SECRET}",
            target_type=f"target-{SECRET}",
            target_id=f"target-id-{SECRET}",
            run_id=f"run-{SECRET}",
            case_id=f"case-{SECRET}",
            team_id=TEAM,
            repo_name=f"repo-{SECRET}",
            created_at=NOW,
            overall_score=8.2,
            grade=f"grade-{SECRET}",
            pass_status=f"pass-{SECRET}",
            dimensions=[
                EvaluationDimension(
                    name=f"dimension-{SECRET}",
                    score=8,
                    weight=1,
                    passed=True,
                    rationale=f"rationale-{SECRET}",
                    evidence=[f"evidence-{SECRET}"],
                    missing_items=[f"missing-{SECRET}"],
                    recommendations=[f"recommend-{SECRET}"],
                )
            ],
            missing_critical_items=[f"critical-{SECRET}"],
            hallucination_warnings=[f"hallucination-{SECRET}"],
            source_coverage={f"coverage-{SECRET}": True},
            recommendations=[f"eval-recommend-{SECRET}"],
            llm_judge=LLMJudgeResult(
                status="completed",
                provider=f"judge-provider-{SECRET}",
                model=f"judge-model-{SECRET}",
                prompt_version=f"prompt-version-{SECRET}",
                input_hash=f"judge-input-{SECRET}",
                readiness=f"readiness-{SECRET}",
                confidence=0.8,
                summary=f"summary-{SECRET}",
                risks=[f"risk-{SECRET}"],
                missing_evidence=[f"judge-missing-{SECRET}"],
                recommendations=[f"judge-recommend-{SECRET}"],
                raw_response=f"raw-response-{SECRET}",
                token_usage={f"token-key-{SECRET}": 11},
                warning=f"judge-warning-{SECRET}",
            ),
            warnings=[f"scorecard-warning-{SECRET}"],
        )
    )

    access = ResourceAccess(
        classification="sensitive",
        acl_scope="source_acl",
        allowed_principal_ids={f"principal-{SECRET}"},
        allowed_group_ids={f"group-{SECRET}"},
        source_acl_version=f"acl-{SECRET}",
        source_acl_lineage={f"acl-parent-{SECRET}"},
    )
    connector = ConnectorLifecycleRepository(artifacts)
    state = ConnectorSourceState(
        source_key="connector-source:" + "a" * 64,
        connector_id=f"connector-{SECRET}",
        source_id=f"source-{SECRET}",
        team_id=TEAM,
        source_type=f"source-type-{SECRET}",
        source_version=f"version-{SECRET}",
        content_hash=f"content-{SECRET}",
        access=access,
        first_seen_at=NOW,
        last_seen_at=NOW,
        deleted_by=f"deleter-{SECRET}",
        deletion_reason=f"delete-reason-{SECRET}",
    )
    event = ConnectorLifecycleEvent(
        event_id=f"event-{SECRET}",
        source_key=state.source_key,
        team_id=TEAM,
        action="activated",
        actor=f"actor-{SECRET}",
        occurred_at=NOW,
        current_source_version=f"version-{SECRET}",
        revoked_acl_versions={f"acl-{SECRET}"},
        purged_artifact_ids=[f"artifact-{SECRET}"],
        warnings=[f"connector-warning-{SECRET}"],
    )
    connector.record(state=state, event=event)

    artifact = artifacts / "derived" / f"artifact-{SECRET}.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")
    ArtifactLineageRegistry(artifacts).register_path(
        team_id=TEAM,
        artifact_kind=f"kind-{SECRET}",
        path=artifact,
        acl_versions={f"acl-{SECRET}"},
        must_exist=True,
    )
    AccessRevocationRegistry(
        artifacts / "pilot-security/access-revocations.json"
    ).revoke(
        team_id=TEAM,
        source_acl_version=f"acl-{SECRET}",
        revoked_by=f"revoker-{SECRET}",
        reason=f"revoke-reason-{SECRET}",
        revoked_at=NOW,
    )

    DlpEventRepository(artifacts).record(
        DlpDecisionEvidence(
            event_id=f"dlp-event-{SECRET}",
            timestamp=NOW,
            policy_version=f"policy-{SECRET}",
            stage="pre_prompt",
            status="blocked",
            team_id=TEAM,
            resource_id_hash=f"resource-{SECRET}",
            classification=f"classification-{SECRET}",
            input_hash=f"dlp-input-{SECRET}",
            output_hash=f"dlp-output-{SECRET}",
            input_char_count=10,
            output_char_count=0,
            redaction_count=0,
            block_count=1,
            findings=[
                DlpFindingEvidence(
                    rule_id=f"rule-{SECRET}",
                    category=f"category-{SECRET}",
                    severity="critical",
                    action="block",
                    fingerprint=f"fingerprint-{SECRET}",
                )
            ],
        )
    )
    DlpEventRepository(artifacts).record(
        DlpDecisionEvidence(
            event_id="other-dlp",
            timestamp=NOW,
            policy_version="other-policy",
            stage="pre_prompt",
            status="allowed",
            team_id=OTHER_TEAM,
            resource_id_hash="other-resource",
            classification="internal",
            input_hash="other-dlp-input",
            output_hash="other-dlp-output",
            input_char_count=1,
            output_char_count=1,
            redaction_count=0,
            block_count=0,
        )
    )
    ProviderEgressRepository(artifacts).record(
        ProviderEgressEvidence(
            timestamp=NOW,
            status="blocked",
            reason_code=f"reason-{SECRET}",
            provider=f"provider-{SECRET}",
            model=f"provider-model-{SECRET}",
            base_url_hash=f"base-url-{SECRET}",
            approval_id=f"approval-{SECRET}",
            manifest_hash=f"manifest-{SECRET}",
        )
    )


def _build(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    db_path = tmp_path / "audit.sqlite"
    _seed_evidence(artifacts, db_path)
    result = PilotEvidenceExporter(
        artifacts_dir=artifacts,
        audit_db_path=db_path,
        mode="private-extension",
    ).build(
        team_id=TEAM,
        confirm_team=TEAM,
        operator_id=f"operator-{SECRET}",
        reason=f"export-reason-{SECRET}",
    )
    return artifacts, db_path, result


def test_evidence_bundle_is_team_scoped_metadata_only_and_verifiable(tmp_path: Path) -> None:
    _, _, result = _build(tmp_path)
    bundle = Path(result.bundle_dir)
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in bundle.iterdir() if path.is_file()
    )

    assert SECRET not in combined
    assert TEAM not in combined
    assert OTHER_TEAM not in combined
    assert "other-team-source" not in combined
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "partial_control_evidence"
    assert manifest["known_coverage_gaps"] == [
        "runtime_identity_decisions_not_persisted",
        "access_policy_decisions_not_persisted",
    ]
    assert {item["source"] for item in manifest["coverage"]} == {
        "audit_runs",
        "human_ratings",
        "evaluations",
        "access_revocations",
        "connector_lifecycle",
        "artifact_lineage",
        "dlp_decisions",
        "provider_egress",
    }
    report = PilotEvidenceVerifier().verify(
        bundle,
        expected_root_sha256=result.bundle_root_sha256,
    )
    assert report.passed
    assert report.expected_root_matched is True


def test_evidence_verifier_detects_file_tamper_and_wrong_root(tmp_path: Path) -> None:
    _, _, result = _build(tmp_path)
    bundle = Path(result.bundle_dir)
    audit_file = bundle / "audit-runs.json"
    audit_file.write_text(audit_file.read_text(encoding="utf-8") + " ", encoding="utf-8")

    report = PilotEvidenceVerifier().verify(
        bundle,
        expected_root_sha256="0" * 64,
    )

    assert not report.passed
    assert "file:audit-runs.json" in report.failures
    assert "expected_root" in report.failures


def test_evidence_verifier_rejects_extra_file(tmp_path: Path) -> None:
    _, _, result = _build(tmp_path)
    bundle = Path(result.bundle_dir)
    (bundle / "untracked-secret.txt").write_text(SECRET, encoding="utf-8")

    report = PilotEvidenceVerifier().verify(bundle)

    assert not report.passed
    assert "exact_file_set" in report.failures


def test_evidence_verifier_rejects_free_text_even_with_recomputed_hashes(
    tmp_path: Path,
) -> None:
    _, _, result = _build(tmp_path)
    bundle = Path(result.bundle_dir)
    section_path = bundle / "audit-runs.json"
    section = json.loads(section_path.read_text(encoding="utf-8"))
    section["records"].append({SECRET: 1})
    section_path.write_text(
        json.dumps(section, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checksum = next(item for item in manifest["files"] if item["path"] == section_path.name)
    checksum["sha256"] = hashlib.sha256(section_path.read_bytes()).hexdigest()
    checksum["size_bytes"] = section_path.stat().st_size
    coverage = next(
        item for item in manifest["coverage"] if item["source"] == "audit_runs"
    )
    coverage["record_count"] += 1
    root_payload = {key: value for key, value in manifest.items() if key != "bundle_root_sha256"}
    manifest["bundle_root_sha256"] = hashlib.sha256(
        json.dumps(
            root_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    report = PilotEvidenceVerifier().verify(bundle)

    assert not report.passed
    assert "section:audit-runs.json" in report.failures


def test_evidence_verifier_rejects_hidden_coverage_gap_with_recomputed_root(
    tmp_path: Path,
) -> None:
    _, _, result = _build(tmp_path)
    bundle = Path(result.bundle_dir)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["known_coverage_gaps"] = []
    root_payload = {
        key: value for key, value in manifest.items() if key != "bundle_root_sha256"
    }
    manifest["bundle_root_sha256"] = hashlib.sha256(
        json.dumps(
            root_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    report = PilotEvidenceVerifier().verify(bundle)

    assert not report.passed
    assert report.checks["bundle_root"] is True
    assert "known_gaps_contract" in report.failures


def test_evidence_verifier_rejects_non_sha256_manifest_fields(tmp_path: Path) -> None:
    _, _, result = _build(tmp_path)
    manifest_path = Path(result.manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["coverage"][0]["source_snapshot_sha256"] = SECRET
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    report = PilotEvidenceVerifier().verify(Path(result.bundle_dir))

    assert not report.passed
    assert report.failures == ["manifest_invalid"]


def test_evidence_export_requires_exact_team_confirmation_and_safe_output(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    exporter = PilotEvidenceExporter(
        artifacts_dir=artifacts,
        audit_db_path=tmp_path / "audit.sqlite",
        mode="private-extension",
    )
    with pytest.raises(DreamError, match="confirmation"):
        exporter.build(
            team_id=TEAM,
            confirm_team=OTHER_TEAM,
            operator_id="operator",
            reason="reason",
        )
    with pytest.raises(PathTraversalError):
        exporter.build(
            team_id=TEAM,
            confirm_team=TEAM,
            operator_id="operator",
            reason="reason",
            output_root=tmp_path / "outside",
        )
    with pytest.raises(PathTraversalError):
        exporter.build(
            team_id=TEAM,
            confirm_team=TEAM,
            operator_id="operator",
            reason="reason",
            output_root=artifacts / "pilot-security/export",
        )


def test_invalid_source_fails_closed_and_removes_partial_bundle(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    control = artifacts / "pilot-security"
    control.mkdir(parents=True)
    (control / "connector-source-lifecycle.json").write_text(
        "not valid json",
        encoding="utf-8",
    )
    output_root = artifacts / "pilot-evidence"
    exporter = PilotEvidenceExporter(
        artifacts_dir=artifacts,
        audit_db_path=tmp_path / "audit.sqlite",
        mode="private-extension",
    )

    with pytest.raises(DreamError, match="ledger"):
        exporter.build(
            team_id=TEAM,
            confirm_team=TEAM,
            operator_id="operator",
            reason="reason",
            output_root=output_root,
        )

    assert output_root.exists()
    assert list(output_root.iterdir()) == []


def test_invalid_evaluation_payload_fails_closed_without_echoing_payload(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    db_path = tmp_path / "audit.sqlite"
    _seed_evidence(artifacts, db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE evaluation_scorecards SET payload = ?",
            (f'{{"private":"{SECRET}"}}',),
        )
    output_root = artifacts / "pilot-evidence"
    exporter = PilotEvidenceExporter(
        artifacts_dir=artifacts,
        audit_db_path=db_path,
        mode="private-extension",
    )

    with pytest.raises(DreamError) as error:
        exporter.build(
            team_id=TEAM,
            confirm_team=TEAM,
            operator_id="operator",
            reason="reason",
            output_root=output_root,
        )

    assert str(error.value) == "Pilot evidence evaluation source is unreadable or invalid."
    assert SECRET not in str(error.value)
    assert list(output_root.iterdir()) == []


def test_audit_cli_exports_and_verifies_empty_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifacts))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "audit.sqlite"))
    runner = CliRunner()

    exported = runner.invoke(
        app,
        [
            "audit",
            "export-bundle",
            "--team",
            "demo-team",
            "--confirm-team",
            "demo-team",
            "--operator",
            "demo-operator",
            "--reason",
            "synthetic validation",
        ],
    )

    assert exported.exit_code == 0, exported.output
    payload = json.loads(exported.output)
    verified = runner.invoke(
        app,
        [
            "audit",
            "verify-bundle",
            "--bundle",
            payload["bundle_dir"],
            "--expected-root-sha256",
            payload["bundle_root_sha256"],
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["passed"] is True
