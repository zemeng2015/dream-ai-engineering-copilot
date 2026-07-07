# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_alibaba_proof_capture_and_validation_include_showcase_endpoint() -> None:
    capture = (ROOT / "scripts" / "qwencloud-capture-alibaba-proof.ps1").read_text(
        encoding="utf-8-sig"
    )
    validate = (ROOT / "scripts" / "qwencloud-validate-alibaba-proof.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "/qwencloud/showcase" in capture
    assert "showcase_track_memoryagent" in capture
    assert "showcase_static_evidence_ready" in capture
    assert "showcase_live_backend_ready" in capture
    assert "showcase = $showcase" in capture

    assert "showcase_present" in validate
    assert "showcase_runtime_provider_qwen_cloud" in validate
    assert "showcase_static_evidence_ready" in validate
    assert "showcase_live_backend_ready" in validate


def test_deploy_preflight_uses_isolated_showcase_smoke() -> None:
    preflight = (ROOT / "scripts" / "qwencloud-deploy-preflight.ps1").read_text(
        encoding="utf-8-sig"
    )
    readiness = (ROOT / "scripts" / "qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "Resolve-SmokePort" in preflight
    assert "docker.smoke_port_available" in preflight
    assert "/qwencloud/showcase" in preflight
    assert "docker.smoke_showcase" in preflight
    assert 'Where-Object { $_.name -eq "docker.smoke_showcase" }' in readiness
    assert "docker.smoke_showcase=$($showcaseCheck.ok)" in readiness
    assert "[bool]$showcaseCheck.ok" in readiness


def test_hackathon_verify_and_proof_collect_showcase_endpoint() -> None:
    verify = (ROOT / "scripts" / "qwencloud-hackathon-verify.ps1").read_text(
        encoding="utf-8-sig"
    )
    proof = (ROOT / "scripts" / "qwencloud-hackathon-proof.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "/qwencloud/showcase" in verify
    assert "Showcase proof passed." in verify
    assert "weighted_static_evidence_ready" in verify
    assert "showcase runtime provider" in verify

    assert 'Join-Path $OutputDir "showcase-$timestamp.json"' in proof
    assert "/qwencloud/showcase" in proof
    assert "Collecting showcase proof" in proof


def test_post_submit_verification_requires_showcase_endpoint() -> None:
    post_submit = (ROOT / "scripts" / "qwencloud-post-submit-verification.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "/qwencloud/showcase" in post_submit
    assert "backend_showcase_reachable" in post_submit
    assert "backend_showcase_track_memoryagent" in post_submit
    assert "backend_showcase_provider_qwen_cloud" in post_submit
    assert "backend_showcase_static_evidence_ready" in post_submit
    assert "backend_showcase_live_backend_ready" in post_submit
