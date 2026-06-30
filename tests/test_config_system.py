# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import yaml

from dream.config import load_config, resolve_config, sanitized_config_dict, validate_config


def test_config_loads_from_default_file(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_CONFIG_FILE", raising=False)
    monkeypatch.delenv("DREAM_ARTIFACT_ROOT", raising=False)

    config = load_config()

    assert config.mode == "public-demo"
    assert config.llm.provider == "mock"


def test_config_loads_from_dream_config_file(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "dream.private.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "mode": "private-extension",
                "llm": {"provider": "mock"},
                "artifacts": {"root": str(tmp_path / "artifacts")},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))

    resolved = resolve_config()

    assert resolved.mode == "private-extension"
    assert resolved.artifacts.root == (tmp_path / "artifacts").resolve()


def test_env_var_resolution_does_not_print_secret_values(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "mode": "public-demo",
                "llm": {
                    "provider": "openai-compatible",
                    "base_url_env": "EXAMPLE_BASE_URL",
                    "api_key_env": "EXAMPLE_API_KEY",
                },
                "artifacts": {"root": str(tmp_path / "artifacts")},
                "audit": {"sqlite_path": str(tmp_path / "dream.sqlite")},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("EXAMPLE_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("EXAMPLE_API_KEY", "super-secret-value")

    resolved = resolve_config()
    sanitized = sanitized_config_dict(resolved)

    assert resolved.llm.api_key_configured is True
    assert "super-secret-value" not in str(sanitized)
    assert sanitized["llm"]["api_key_value"] == "[not displayed]"


def test_plugin_class_loading_from_config(tmp_path, monkeypatch) -> None:
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text("class SampleProvider:\n    pass\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    config_path = _config_file(
        tmp_path,
        {
            "llm": {
                "provider": "plugin",
                "class_path": "sample_plugin:SampleProvider",
            }
        },
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))

    report = validate_config()

    assert report.ok


def test_invalid_plugin_class_gives_clear_error(tmp_path, monkeypatch) -> None:
    config_path = _config_file(
        tmp_path,
        {
            "llm": {
                "provider": "plugin",
                "class_path": "missing_module:MissingProvider",
            }
        },
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))

    report = validate_config()

    assert not report.ok
    assert any("plugin failed to load" in item.message for item in report.diagnostics)


def test_config_doctor_private_extension_warns_for_public_repo_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    public_artifact_root = Path("artifacts/private-mode-test")
    config_path = _config_file(
        tmp_path,
        {
            "mode": "private-extension",
            "artifacts": {"root": str(public_artifact_root)},
        },
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))

    report = validate_config(create_artifact_root=False)

    assert report.ok
    assert any("inside the public repo" in item.message for item in report.diagnostics)


def _config_file(tmp_path: Path, overrides: dict[str, object]) -> Path:
    payload = {
        "mode": "public-demo",
        "llm": {"provider": "mock"},
        "knowledge": {"pack_root": "knowledge_packs"},
        "artifacts": {"root": str(tmp_path / "artifacts")},
        "audit": {"sqlite_path": str(tmp_path / "dream.sqlite")},
    }
    payload.update(overrides)
    path = tmp_path / "dream.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path
