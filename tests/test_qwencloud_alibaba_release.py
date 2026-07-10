# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_container_fallback_login_is_isolated_from_primary_runtime_workflow() -> None:
    release = (ROOT / "scripts" / "qwencloud-alibaba-release.ps1").read_text(
        encoding="utf-8-sig"
    )
    workflow = (ROOT / ".github" / "workflows" / "qwencloud-release.yml").read_text(
        encoding="utf-8-sig"
    )

    assert "function Invoke-DockerLogin" in release
    assert "ALIBABA_CONTAINER_REGISTRY_USERNAME" in release
    assert "ALIBABA_CONTAINER_REGISTRY_PASSWORD" in release
    assert "unless -SkipPush is set" in release
    assert "--password-stdin" in release
    assert "Invoke-DockerLogin -RegistryHost $registryHost" in release
    assert release.index("Invoke-DockerLogin -RegistryHost $registryHost") < release.index(
        'Invoke-Logged -FilePath "docker" -ArgumentList @("push", $containerImage)'
    )
    assert "docker login $RegistryHost with ALIBABA_CONTAINER_REGISTRY_USERNAME" in release
    assert "docker login $registryHost -u $env:ALIBABA_CONTAINER_REGISTRY_USERNAME" not in release

    assert "ALIBABA_CONTAINER_REGISTRY_PASSWORD | docker login" not in workflow
    assert "qwencloud-alibaba-runtime-release.ps1" in workflow
    assert "qwencloud-alibaba-release.ps1" not in workflow
    assert 'python-version: "3.12"' in workflow
