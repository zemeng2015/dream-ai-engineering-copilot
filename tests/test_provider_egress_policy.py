# SPDX-License-Identifier: Apache-2.0

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import typer
from fastapi import HTTPException

from dream.api import routes
from dream.cli import main as cli_main
from dream.config import DreamConfig, resolve_config, validate_config
from dream.core.errors import ProviderConfigurationError
from dream.extensions import build_llm_provider
from dream.llm import LLMResponse
from dream.llm.egress import (
    APPROVAL_FILE_ENV,
    ProviderEgressPolicy,
    ProviderEgressRepository,
    normalize_provider_base_url,
    require_private_provider_selector,
)


def _private_config(tmp_path: Path, *, model: str = "gpt-5.4"):
    return resolve_config(
        DreamConfig.model_validate(
            {
                "mode": "private-extension",
                "llm": {
                    "provider": "openai-compatible",
                    "base_url": "https://api.openai.com/v1/",
                    "model": model,
                    "api_key_env": "PILOT_OPENAI_API_KEY",
                },
                "artifacts": {"root": str(tmp_path / "artifacts")},
                "audit": {"sqlite_path": str(tmp_path / "audit.sqlite")},
            }
        )
    )


def _approval_file(
    tmp_path: Path,
    *,
    provider: str = "openai-compatible",
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-5.4",
    expired: bool = False,
) -> Path:
    now = datetime.now(UTC)
    path = tmp_path / "provider-approval.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "provider-approval-v1",
                "approval_id": "security-change-1234",
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "approved_by": "security-reviewer",
                "approved_at": (now - timedelta(days=2)).isoformat(),
                "expires_at": (
                    now - timedelta(days=1) if expired else now + timedelta(days=30)
                ).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_private_provider_requires_external_exact_unexpired_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _private_config(tmp_path)
    repository = ProviderEgressRepository(config.artifacts.root)
    policy = ProviderEgressPolicy(repository)
    monkeypatch.delenv(APPROVAL_FILE_ENV, raising=False)

    with pytest.raises(ProviderConfigurationError, match="approval_file_not_configured"):
        policy.require_approved(config)

    approval = _approval_file(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(approval))
    manifest = policy.require_approved(config)

    assert manifest is not None
    assert manifest.approval_id == "security-change-1234"
    events = repository.load()
    assert [event.status for event in events] == ["blocked", "allowed"]
    assert events[-1].reason_code == "exact_approval_match"
    ledger = repository.path.read_text(encoding="utf-8")
    assert "https://api.openai.com" not in ledger
    assert str(approval) not in ledger


@pytest.mark.parametrize(
    ("approval_kwargs", "reason"),
    [
        ({"model": "different-model"}, "approval_identity_mismatch"),
        ({"base_url": "https://approved.example/v1"}, "approval_identity_mismatch"),
        ({"expired": True}, "approval_expired"),
    ],
)
def test_private_provider_rejects_mismatch_and_expiration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approval_kwargs: dict[str, object],
    reason: str,
) -> None:
    config = _private_config(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(_approval_file(tmp_path, **approval_kwargs)))

    with pytest.raises(ProviderConfigurationError, match=reason):
        ProviderEgressPolicy().require_approved(config)


def test_private_provider_build_records_approval_and_preserves_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _private_config(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(_approval_file(tmp_path)))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")

    provider = build_llm_provider(config)

    assert provider.provider_name == "openai-compatible"
    assert provider.model_name == "gpt-5.4"
    event = ProviderEgressRepository(config.artifacts.root).load()[-1]
    assert event.status == "allowed"
    assert event.approval_id == "security-change-1234"


def test_private_provider_rechecks_expiration_before_every_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _private_config(tmp_path)
    approval = _approval_file(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(approval))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")
    network_called = False

    def fail_if_called(request, timeout):  # noqa: ANN001, ARG001
        nonlocal network_called
        network_called = True
        raise AssertionError("network must not be called after approval expiry")

    monkeypatch.setattr("dream.llm.openai_compatible.urlopen", fail_if_called)
    provider = build_llm_provider(config)
    _approval_file(tmp_path, expired=True)

    with pytest.raises(ProviderConfigurationError, match="approval_expired"):
        provider.complete("do not send")

    assert network_called is False


def test_private_provider_blocks_unapproved_response_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _private_config(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(_approval_file(tmp_path)))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")
    provider = build_llm_provider(config)
    provider.provider.provider.complete = lambda prompt: LLMResponse(  # type: ignore[method-assign]
        text="should not escape",
        provider_name="openai-compatible",
        model_name="unapproved-model",
    )

    with pytest.raises(ProviderConfigurationError, match="response_identity_mismatch"):
        provider.complete("safe prompt")

    event = ProviderEgressRepository(config.artifacts.root).load()[-1]
    assert event.status == "blocked"
    assert event.reason_code == "response_identity_mismatch"
    assert "unapproved-model" not in ProviderEgressRepository(
        config.artifacts.root
    ).path.read_text(encoding="utf-8")


def test_private_provider_blocks_runtime_endpoint_mutation_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _private_config(tmp_path)
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(_approval_file(tmp_path)))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")
    network_called = False

    def fail_if_called(request, timeout):  # noqa: ANN001, ARG001
        nonlocal network_called
        network_called = True
        raise AssertionError("network must not be called after endpoint mutation")

    monkeypatch.setattr("dream.llm.openai_compatible.urlopen", fail_if_called)
    provider = build_llm_provider(config)
    provider.provider.provider.base_url = "https://unapproved.example/v1"

    with pytest.raises(
        ProviderConfigurationError,
        match="runtime_provider_identity_mismatch",
    ):
        provider.complete("do not send")

    assert network_called is False
    ledger = ProviderEgressRepository(config.artifacts.root).path.read_text(encoding="utf-8")
    assert "unapproved.example" not in ledger


def test_private_plugin_provider_is_denied_before_extension_loading(tmp_path: Path) -> None:
    config = resolve_config(
        DreamConfig.model_validate(
            {
                "mode": "private-extension",
                "llm": {"provider": "plugin", "class_path": "missing:Provider"},
                "artifacts": {"root": str(tmp_path / "artifacts")},
            }
        )
    )

    with pytest.raises(ProviderConfigurationError, match="private_plugin_provider_not_attested"):
        build_llm_provider(config)


def test_private_mode_blocks_request_and_cli_live_provider_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "dream.private.yaml"
    config_path.write_text(
        "\n".join(
            [
                "mode: private-extension",
                "llm:",
                "  provider: mock",
                "artifacts:",
                f"  root: '{(tmp_path / 'artifacts').as_posix()}'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))

    with pytest.raises(HTTPException) as api_error:
        routes._llm_provider("openai-compatible")
    assert api_error.value.status_code == 403
    with pytest.raises(typer.BadParameter, match="request-level live provider overrides"):
        cli_main._llm_provider("qwen-cloud")
    assert routes._llm_provider("mock").provider_name == "mock"


def test_selector_contract_allows_only_safe_private_choices(tmp_path: Path) -> None:
    config = resolve_config(
        DreamConfig.model_validate(
            {
                "mode": "private-extension",
                "llm": {"provider": "mock"},
                "artifacts": {"root": str(tmp_path / "artifacts")},
            }
        )
    )
    for allowed in ["mock", "deterministic", "none", "config"]:
        require_private_provider_selector(allowed, config=config)
    for denied in ["openai-compatible", "qwen-cloud", "plugin"]:
        with pytest.raises(ProviderConfigurationError):
            require_private_provider_selector(denied, config=config)


def test_config_validator_fails_private_live_provider_without_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "dream.private.yaml"
    config_path.write_text(
        "\n".join(
            [
                "mode: private-extension",
                "llm:",
                "  provider: openai-compatible",
                "  model: gpt-5.4",
                "  base_url: https://api.openai.com/v1",
                "  api_key_env: PILOT_OPENAI_API_KEY",
                "artifacts:",
                f"  root: '{(tmp_path / 'artifacts').as_posix()}'",
                "audit:",
                f"  sqlite_path: '{(tmp_path / 'audit.sqlite').as_posix()}'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")
    monkeypatch.delenv(APPROVAL_FILE_ENV, raising=False)

    report = validate_config()

    assert not report.ok
    assert any("approval_file_not_configured" in item.message for item in report.diagnostics)


def test_config_validator_accepts_exact_private_provider_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "dream.private.yaml"
    config_path.write_text(
        "\n".join(
            [
                "mode: private-extension",
                "llm:",
                "  provider: openai-compatible",
                "  model: gpt-5.4",
                "  base_url: https://api.openai.com/v1",
                "  api_key_env: PILOT_OPENAI_API_KEY",
                "artifacts:",
                f"  root: '{(tmp_path / 'artifacts').as_posix()}'",
                "audit:",
                f"  sqlite_path: '{(tmp_path / 'audit.sqlite').as_posix()}'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("PILOT_OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv(APPROVAL_FILE_ENV, str(_approval_file(tmp_path)))

    report = validate_config()

    assert report.ok
    assert not any("provider egress denied" in item.message.lower() for item in report.diagnostics)


def test_config_validator_rejects_private_plugin_without_importing_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "dream.private.yaml"
    config_path.write_text(
        "\n".join(
            [
                "mode: private-extension",
                "llm:",
                "  provider: plugin",
                "  class_path: unsafe_plugin:Provider",
                "artifacts:",
                f"  root: '{(tmp_path / 'artifacts').as_posix()}'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    imported = False

    def fail_if_imported(class_path):  # noqa: ANN001, ARG001
        nonlocal imported
        imported = True
        raise AssertionError("private plugin must be denied before import")

    monkeypatch.setattr("dream.config.validator.load_class", fail_if_imported)
    report = validate_config()

    assert not report.ok
    assert imported is False
    assert any(
        "private_plugin_provider_not_attested" in item.message
        for item in report.diagnostics
    )


@pytest.mark.parametrize(
    "value",
    [
        "http://provider.example/v1",
        "https://user:password@provider.example/v1",
        "https://provider.example/v1?redirect=https://evil.example",
        "https://provider.example/v1/../admin",
        "https://provider.example/v1/%2e%2e/admin",
        "https://provider.example/v1//shadow",
        "https://provider.example./v1",
    ],
)
def test_provider_base_url_rejects_insecure_or_ambiguous_remote_targets(value: str) -> None:
    with pytest.raises(ProviderConfigurationError):
        normalize_provider_base_url(value)


def test_provider_base_url_allows_public_loopback_but_private_requires_https() -> None:
    assert normalize_provider_base_url("http://127.0.0.1:8080/v1/") == (
        "http://127.0.0.1:8080/v1"
    )
    with pytest.raises(ProviderConfigurationError):
        normalize_provider_base_url("http://127.0.0.1:8080/v1", require_https=True)
    assert normalize_provider_base_url("https://gateway.example:8443/v1/") == (
        "https://gateway.example:8443/v1"
    )
    with pytest.raises(ProviderConfigurationError, match="DNS hostname"):
        normalize_provider_base_url("https://10.0.0.5/v1", require_https=True)
