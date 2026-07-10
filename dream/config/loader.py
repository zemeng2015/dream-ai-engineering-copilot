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
from dream.llm.qwen_cloud import QWEN_CLOUD_BASE_URL, QWEN_CLOUD_DEFAULT_MODEL

DEFAULT_CONFIG_FILE = PROJECT_ROOT / "dream.yaml"
LLM_PROVIDERS = {"mock", "openai-compatible", "qwen-cloud", "plugin"}


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
    provider = os.getenv("DREAM_LLM_PROVIDER", "").strip() or loaded.llm.provider
    if provider not in LLM_PROVIDERS:
        raise ValueError(
            "DREAM_LLM_PROVIDER must be one of: " + ", ".join(sorted(LLM_PROVIDERS))
        )
    provider_overridden = provider != loaded.llm.provider
    configured_model = None if provider_overridden else loaded.llm.model
    configured_base_url = None if provider_overridden else loaded.llm.base_url
    configured_base_url_env = None if provider_overridden else loaded.llm.base_url_env
    configured_api_key_env = None if provider_overridden else loaded.llm.api_key_env
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
    if provider == "qwen-cloud":
        default_base_url = (
            os.getenv("QWEN_BASE_URL")
            or os.getenv("DASHSCOPE_BASE_URL")
            or QWEN_CLOUD_BASE_URL
        )
        default_model = os.getenv("QWEN_MODEL") or QWEN_CLOUD_DEFAULT_MODEL
        resolved_model = os.getenv("QWEN_MODEL") or configured_model or default_model
    else:
        default_base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL") or "https://api.openai.com/v1"
        default_model = os.getenv("OPENAI_COMPATIBLE_MODEL")
        resolved_model = configured_model or default_model
    base_url, base_url_source = _value_from_config_or_env(
        value=configured_base_url,
        env_name=configured_base_url_env,
        default=default_base_url,
    )
    api_key_env = _choose_api_key_env(configured_api_key_env, provider=provider)
    resolved_base_url_env = (
        configured_base_url_env
        if configured_base_url_env
        else base_url_source.removeprefix("env:")
        if base_url_source.startswith("env:")
        else None
    )
    return ResolvedDreamConfig(
        mode=loaded.mode,
        source_file=source_file,
        llm=ResolvedLLMConfig(
            provider=provider,
            model=resolved_model,
            base_url=base_url,
            base_url_env=resolved_base_url_env,
            api_key_env=api_key_env,
            api_key_configured=bool(api_key_env and os.getenv(api_key_env)),
            class_path=None if provider_overridden else loaded.llm.class_path,
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


def _choose_api_key_env(
    configured: str | None,
    *,
    provider: str = "openai-compatible",
) -> str | None:
    if configured:
        return configured
    if provider == "qwen-cloud":
        if os.getenv("DASHSCOPE_API_KEY"):
            return "DASHSCOPE_API_KEY"
        if os.getenv("QWEN_API_KEY"):
            return "QWEN_API_KEY"
        return "DASHSCOPE_API_KEY"
    if os.getenv("OPENAI_COMPATIBLE_API_KEY"):
        return "OPENAI_COMPATIBLE_API_KEY"
    if os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY"
    return "OPENAI_COMPATIBLE_API_KEY"


def _resolve_path(path_value: str | Path, *, base: Path) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(str(path_value))))
    candidate = path if path.is_absolute() else base / path
    return candidate.resolve()
