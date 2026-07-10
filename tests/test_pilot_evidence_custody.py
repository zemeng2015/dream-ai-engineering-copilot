# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from dream.cli.main import app
from dream.core.errors import DreamError, PathTraversalError
from dream.pilot_evidence import (
    PilotEvidenceExporter,
    PilotEvidenceSignatureVerifier,
    PilotEvidenceSigner,
)

KEY_ID = "pilot-custody-key-2026-01"
SIGNER = "approved-pilot-operator"
REASON = "freeze weekly pilot evidence"


def _bundle(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    result = PilotEvidenceExporter(
        artifacts_dir=artifacts,
        audit_db_path=tmp_path / "audit.sqlite",
        mode="private-extension",
    ).build(
        team_id="pilot-team",
        confirm_team="pilot-team",
        operator_id="pilot-operator",
        reason="custody test",
    )
    return artifacts, Path(result.bundle_dir), result


def _ed25519_keys(
    key_dir: Path,
    *,
    password: bytes | None = None,
) -> tuple[Path, Path]:
    key_dir.mkdir(parents=True)
    private_key = Ed25519PrivateKey.generate()
    private_path = key_dir / "evidence-private.pem"
    public_path = key_dir / "evidence-public.pem"
    encryption = (
        serialization.BestAvailableEncryption(password)
        if password is not None
        else serialization.NoEncryption()
    )
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def _sign(tmp_path: Path):
    artifacts, bundle, export_result = _bundle(tmp_path)
    private_key, public_key = _ed25519_keys(tmp_path / "approved-keys")
    signed = PilotEvidenceSigner(artifacts_dir=artifacts).sign(
        bundle_dir=bundle,
        expected_root_sha256=export_result.bundle_root_sha256,
        private_key_path=private_key,
        key_id=KEY_ID,
        signer_id=SIGNER,
        reason=REASON,
    )
    return bundle, export_result, private_key, public_key, signed


def test_ed25519_receipt_verifies_without_exposing_operator_metadata(
    tmp_path: Path,
) -> None:
    bundle, export_result, _, public_key, signed = _sign(tmp_path)
    receipt_path = Path(signed.receipt_path)
    receipt_text = receipt_path.read_text(encoding="utf-8")

    assert receipt_path.parent == bundle.parent
    assert not receipt_path.is_relative_to(bundle)
    assert KEY_ID not in receipt_text
    assert SIGNER not in receipt_text
    assert REASON not in receipt_text
    report = PilotEvidenceSignatureVerifier().verify(
        bundle_dir=bundle,
        receipt_path=receipt_path,
        public_key_path=public_key,
        expected_key_id=KEY_ID,
    )
    assert report.passed
    assert report.bundle_root_sha256 == export_result.bundle_root_sha256
    assert report.expected_key_id_matched is True
    assert all(report.checks.values())


def test_signature_verifier_rejects_wrong_key_and_expected_key_id(tmp_path: Path) -> None:
    bundle, _, _, _, signed = _sign(tmp_path)
    _, wrong_public = _ed25519_keys(tmp_path / "wrong-keys")

    report = PilotEvidenceSignatureVerifier().verify(
        bundle_dir=bundle,
        receipt_path=Path(signed.receipt_path),
        public_key_path=wrong_public,
        expected_key_id="wrong-key-id",
    )

    assert not report.passed
    assert "public_key_fingerprint" in report.failures
    assert "expected_key_id" in report.failures
    assert "signature" in report.failures

    artifact_public = bundle.parents[1] / "co-located-public.pem"
    artifact_public.write_bytes(wrong_public.read_bytes())
    co_located = PilotEvidenceSignatureVerifier(
        artifacts_dir=bundle.parents[1]
    ).verify(
        bundle_dir=bundle,
        receipt_path=Path(signed.receipt_path),
        public_key_path=artifact_public,
    )
    assert not co_located.passed
    assert "public_key_invalid" in co_located.failures


def test_signature_verifier_rejects_receipt_and_bundle_tamper(tmp_path: Path) -> None:
    bundle, _, _, public_key, signed = _sign(tmp_path)
    receipt_path = Path(signed.receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["reason_hash"] = "0" * 64
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    receipt_report = PilotEvidenceSignatureVerifier().verify(
        bundle_dir=bundle,
        receipt_path=receipt_path,
        public_key_path=public_key,
    )
    assert not receipt_report.passed
    assert "signature" in receipt_report.failures

    (bundle / "audit-runs.json").write_text("{}\n", encoding="utf-8")
    bundle_report = PilotEvidenceSignatureVerifier().verify(
        bundle_dir=bundle,
        receipt_path=receipt_path,
        public_key_path=public_key,
    )
    assert not bundle_report.passed
    assert "bundle_internal" in bundle_report.failures


def test_signer_refuses_invalid_bundle_overwrite_and_unsafe_output(tmp_path: Path) -> None:
    artifacts, bundle, export_result = _bundle(tmp_path)
    private_key, _ = _ed25519_keys(tmp_path / "approved-keys")
    signer = PilotEvidenceSigner(artifacts_dir=artifacts)

    with pytest.raises(DreamError, match="internal verification"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256="0" * 64,
            private_key_path=private_key,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )
    signed = signer.sign(
        bundle_dir=bundle,
        expected_root_sha256=export_result.bundle_root_sha256,
        private_key_path=private_key,
        key_id=KEY_ID,
        signer_id=SIGNER,
        reason=REASON,
    )
    with pytest.raises(DreamError, match="overwrite"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=private_key,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )
    with pytest.raises(PathTraversalError, match="cannot enter the bundle"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=private_key,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
            output_path=bundle / "signature.json",
        )

    Path(signed.receipt_path).unlink()
    (bundle / "audit-runs.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(DreamError, match="internal verification"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=private_key,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )


def test_signer_rejects_checkout_key_relative_key_and_non_ed25519_key(
    tmp_path: Path,
) -> None:
    artifacts, bundle, export_result = _bundle(tmp_path)
    project = tmp_path / "public-checkout"
    private_key, _ = _ed25519_keys(project / "keys")
    signer = PilotEvidenceSigner(artifacts_dir=artifacts, project_root=project)

    with pytest.raises(PathTraversalError, match="outside the public checkout"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=private_key,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )
    with pytest.raises(PathTraversalError, match="absolute"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=Path("relative-key.pem"),
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )

    artifact_private, _ = _ed25519_keys(artifacts / "co-located-keys")
    with pytest.raises(PathTraversalError, match="outside the artifact root"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=artifact_private,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )

    rsa_path = tmp_path / "approved-rsa.pem"
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_path.write_bytes(
        rsa_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    with pytest.raises(DreamError, match="Ed25519"):
        signer.sign(
            bundle_dir=bundle,
            expected_root_sha256=export_result.bundle_root_sha256,
            private_key_path=rsa_path,
            key_id=KEY_ID,
            signer_id=SIGNER,
            reason=REASON,
        )


def test_encrypted_private_key_uses_named_environment_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts, bundle, export_result = _bundle(tmp_path)
    password = b"test-only-key-password"
    private_key, public_key = _ed25519_keys(
        tmp_path / "approved-keys",
        password=password,
    )
    monkeypatch.setenv("TEST_EVIDENCE_KEY_PASSWORD", password.decode("ascii"))

    signed = PilotEvidenceSigner(artifacts_dir=artifacts).sign(
        bundle_dir=bundle,
        expected_root_sha256=export_result.bundle_root_sha256,
        private_key_path=private_key,
        key_id=KEY_ID,
        signer_id=SIGNER,
        reason=REASON,
        private_key_password_env="TEST_EVIDENCE_KEY_PASSWORD",
    )

    assert PilotEvidenceSignatureVerifier().verify(
        bundle_dir=bundle,
        receipt_path=Path(signed.receipt_path),
        public_key_path=public_key,
        expected_key_id=KEY_ID,
    ).passed


def test_audit_cli_signs_and_verifies_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts, bundle, export_result = _bundle(tmp_path)
    private_key, public_key = _ed25519_keys(tmp_path / "approved-keys")
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifacts))
    runner = CliRunner()

    signed = runner.invoke(
        app,
        [
            "audit",
            "sign-bundle",
            "--bundle",
            str(bundle),
            "--expected-root-sha256",
            export_result.bundle_root_sha256,
            "--private-key",
            str(private_key),
            "--key-id",
            KEY_ID,
            "--signer",
            SIGNER,
            "--reason",
            REASON,
        ],
    )
    assert signed.exit_code == 0, signed.output
    receipt_path = json.loads(signed.output)["receipt_path"]

    verified = runner.invoke(
        app,
        [
            "audit",
            "verify-signature",
            "--bundle",
            str(bundle),
            "--receipt",
            receipt_path,
            "--public-key",
            str(public_key),
            "--expected-key-id",
            KEY_ID,
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["passed"] is True
