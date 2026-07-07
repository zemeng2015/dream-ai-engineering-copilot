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

    assert "Resolve-SmokePort" in preflight
    assert "docker.smoke_port_available" in preflight
    assert "/qwencloud/showcase" in preflight
    assert "docker.smoke_showcase" in preflight
