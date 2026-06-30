# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from typing import Any

import yaml

from dream.config.models import (
    DreamConfig,
    ResolvedAuditConfig,
    ResolvedDreamConfig,
    ResolvedLLMConfig,
    ResolvedPathConfig,
    ResolvedProviderConfig,
)
from dream.core.paths import (
    DEFAULT_ARTIFACTS_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_KNOWLEDGE_PACKS_DIR,
    PROJECT_ROOT,
)

DEFAULT_CONFIG_FILE = PROJECT_ROOT / "dream.yaml"


def find_config_file(config_file: str | Path | None = None) -> Path | None:
    explicit = config_file or os.getenv("DREAM_CONFIG_FILE")
    if explicit:
        return _resolve_path(explicit, base=PROJECT_ROOT)
    return DEFAULT_CONFIG_FILE if DEFAULT_CONFIG_FILE.exists() else None


def load_config(config_file: str | Path | None = None) -> DreamConfig:
    path = find_config_file(config_file)
    if path is None:
        return DreamConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"DREAM config must be a mapping: {path}")
    return DreamConfig.model_validate(data)


def resolve_config(
    config: DreamConfig | None = None,
    *,
    config_file: str | Path | None = None,
) -> ResolvedDreamConfig:
    loaded = config or load_config(config_file)
    source_file = find_config_file(config_file) if config is None or config_file else None
    knowledge_root, knowledge_source = _path_from_config_or_env(
        value=loaded.knowledge.pack_root,
        env_name=loaded.knowledge.pack_root_env,
        default=DEFAULT_KNOWLEDGE_PACKS_DIR,
        default_source="default",
    )
    artifact_root, artifact_source = _path_from_config_or_env(
        value=loaded.artifacts.root,
        env_name=loaded.artifacts.root_env,
        default=DEFAULT_ARTIFACTS_DIR,
        default_source="default",
        hard_override_env="DREAM_ARTIFACT_ROOT",
    )
    audit_path, audit_source = _path_from_config_or_env(
        value=loaded.audit.sqlite_path,
        env_name=loaded.audit.sqlite_path_env,
        default=DEFAULT_DB_PATH,
        default_source="default",
        hard_override_env="DREAM_AUDIT_DB_PATH",
    )
    base_url, base_url_source = _value_from_config_or_env(
        value=loaded.llm.base_url,
        env_name=loaded.llm.base_url_env,
        default=os.getenv("OPENAI_COMPATIBLE_BASE_URL") or "https://api.openai.com/v1",
    )
    api_key_env = _choose_api_key_env(loaded.llm.api_key_env)
    resolved_base_url_env = (
        loaded.llm.base_url_env
        if loaded.llm.base_url_env
        else base_url_source.removeprefix("env:")
        if base_url_source.startswith("env:")
        else None
    )
    return ResolvedDreamConfig(
        mode=loaded.mode,
        source_file=source_file,
        llm=ResolvedLLMConfig(
            provider=loaded.llm.provider,
            model=loaded.llm.model or os.getenv("OPENAI_COMPATIBLE_MODEL"),
            base_url=base_url,
            base_url_env=resolved_base_url_env,
            api_key_env=api_key_env,
            api_key_configured=bool(api_key_env and os.getenv(api_key_env)),
            class_path=loaded.llm.class_path,
        ),
        knowledge=ResolvedPathConfig(root=knowledge_root, source=knowledge_source),
        artifacts=ResolvedPathConfig(root=artifact_root, source=artifact_source),
        audit=ResolvedAuditConfig(sqlite_path=audit_path, source=audit_source),
        redaction=ResolvedProviderConfig(
            provider=loaded.redaction.provider,
            class_path=loaded.redaction.class_path,
        ),
        prompt_policy=ResolvedProviderConfig(
            provider=loaded.prompt_policy.provider,
            class_path=loaded.prompt_policy.class_path,
        ),
    )


def sanitized_config_dict(resolved: ResolvedDreamConfig) -> dict[str, Any]:
    payload = resolved.model_dump(mode="json")
    payload["llm"]["api_key_value"] = "[not displayed]"
    return payload


def _path_from_config_or_env(
    *,
    value: str | None,
    env_name: str | None,
    default: Path,
    default_source: str,
    hard_override_env: str | None = None,
) -> tuple[Path, str]:
    if hard_override_env and os.getenv(hard_override_env):
        return (
            _resolve_path(os.environ[hard_override_env], base=PROJECT_ROOT),
            f"env:{hard_override_env}",
        )
    if env_name and os.getenv(env_name):
        return _resolve_path(os.environ[env_name], base=PROJECT_ROOT), f"env:{env_name}"
    if value:
        return _resolve_path(value, base=PROJECT_ROOT), "config"
    return default.resolve(), default_source


def _value_from_config_or_env(
    *,
    value: str | None,
    env_name: str | None,
    default: str | None,
) -> tuple[str | None, str]:
    if env_name and os.getenv(env_name):
        return os.environ[env_name], f"env:{env_name}"
    if value:
        return value, "config"
    return default, "default"


def _choose_api_key_env(configured: str | None) -> str | None:
    if configured:
        return configured
    if os.getenv("OPENAI_COMPATIBLE_API_KEY"):
        return "OPENAI_COMPATIBLE_API_KEY"
    if os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY"
    return "OPENAI_COMPATIBLE_API_KEY"


def _resolve_path(path_value: str | Path, *, base: Path) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(str(path_value))))
    candidate = path if path.is_absolute() else base / path
    return candidate.resolve()
