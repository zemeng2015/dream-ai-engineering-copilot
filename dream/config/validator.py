# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from pathlib import Path

from pydantic import ValidationError

from dream.config.loader import load_config, resolve_config
from dream.config.models import ConfigDiagnostic, ConfigValidationReport, DreamConfig
from dream.core.errors import ProviderConfigurationError
from dream.core.paths import PROJECT_ROOT
from dream.extensions.errors import ExtensionLoadError
from dream.extensions.loader import load_class
from dream.llm.egress import ProviderEgressPolicy


def validate_config(
    *,
    config_file: str | Path | None = None,
    create_artifact_root: bool = True,
) -> ConfigValidationReport:
    diagnostics: list[ConfigDiagnostic] = []
    try:
        config = load_config(config_file)
        resolved = resolve_config(config, config_file=config_file)
    except (OSError, ValueError, ValidationError) as exc:
        fallback = resolve_config(DreamConfig())
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"Config file is invalid: {exc}",
                recommended_fix="Fix dream.yaml syntax and field names, then rerun validation.",
            )
        )
        return ConfigValidationReport(ok=False, config=fallback, diagnostics=diagnostics)

    _check_config_file_exists(config_file, diagnostics)
    _check_declared_env_vars(config, diagnostics)
    _check_llm_provider(config, diagnostics)
    _check_private_provider_approval(resolved, diagnostics)
    if not (resolved.mode == "private-extension" and config.llm.provider == "plugin"):
        _check_plugin("llm", config.llm.provider, config.llm.class_path, diagnostics)
    _check_plugin("redaction", config.redaction.provider, config.redaction.class_path, diagnostics)
    _check_plugin(
        "prompt_policy",
        config.prompt_policy.provider,
        config.prompt_policy.class_path,
        diagnostics,
    )
    _check_knowledge_root(resolved.knowledge.root, diagnostics)
    _check_artifact_root(resolved.artifacts.root, diagnostics, create=create_artifact_root)
    _check_audit_path(resolved.audit.sqlite_path, diagnostics)
    _check_private_artifacts(resolved.mode, resolved.artifacts.root, diagnostics)
    _check_tracked_env(diagnostics)

    return ConfigValidationReport(
        ok=not any(item.severity == "error" for item in diagnostics),
        config=resolved,
        diagnostics=diagnostics,
    )


def _check_config_file_exists(
    config_file: str | Path | None,
    diagnostics: list[ConfigDiagnostic],
) -> None:
    explicit = config_file or os.getenv("DREAM_CONFIG_FILE")
    if explicit and not Path(explicit).expanduser().exists():
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"Configured DREAM config file does not exist: {explicit}",
                recommended_fix="Create the file or update DREAM_CONFIG_FILE.",
            )
        )


def _check_declared_env_vars(config, diagnostics: list[ConfigDiagnostic]) -> None:
    env_fields = [
        ("knowledge.pack_root_env", config.knowledge.pack_root_env),
        ("artifacts.root_env", config.artifacts.root_env),
        ("audit.sqlite_path_env", config.audit.sqlite_path_env),
        ("llm.base_url_env", config.llm.base_url_env),
    ]
    if config.llm.provider in {"openai-compatible", "qwen-cloud"} and config.llm.api_key_env:
        env_fields.append(("llm.api_key_env", config.llm.api_key_env))
    for label, env_name in env_fields:
        if env_name and not os.getenv(env_name):
            if label == "llm.base_url_env" and config.llm.provider in {
                "openai-compatible",
                "qwen-cloud",
            }:
                diagnostics.append(
                    ConfigDiagnostic(
                        severity="warning",
                        message=(
                            f"{label} points to missing environment variable: {env_name}. "
                            "A default base URL will be used if available."
                        ),
                        recommended_fix=(
                            f"Set {env_name}, or hardcode llm.base_url in dream.yaml "
                            "to avoid this warning."
                        ),
                    )
                )
                continue
            diagnostics.append(
                ConfigDiagnostic(
                    severity="error",
                    message=f"{label} points to missing environment variable: {env_name}",
                    recommended_fix=f"Set {env_name} or remove the env reference from dream.yaml.",
                )
            )


def _check_llm_provider(config, diagnostics: list[ConfigDiagnostic]) -> None:
    if config.llm.provider == "openai-compatible":
        env_names = [config.llm.api_key_env] if config.llm.api_key_env else [
            "OPENAI_COMPATIBLE_API_KEY",
            "OPENAI_API_KEY",
        ]
        if not any(env_name and os.getenv(env_name) for env_name in env_names):
            diagnostics.append(
                ConfigDiagnostic(
                    severity="error",
                    message="OpenAI-compatible provider is selected but no API key env var is set.",
                    recommended_fix=(
                        "Set llm.api_key_env in dream.yaml and export that env var, "
                        "or set OPENAI_COMPATIBLE_API_KEY."
                    ),
                )
            )
    if config.llm.provider == "qwen-cloud":
        env_names = [config.llm.api_key_env] if config.llm.api_key_env else [
            "DASHSCOPE_API_KEY",
            "QWEN_API_KEY",
        ]
        if not any(env_name and os.getenv(env_name) for env_name in env_names):
            diagnostics.append(
                ConfigDiagnostic(
                    severity="error",
                    message="Qwen Cloud provider is selected but no API key env var is set.",
                    recommended_fix=(
                        "Set DASHSCOPE_API_KEY, QWEN_API_KEY, or llm.api_key_env in dream.yaml."
                    ),
                )
            )
    if config.llm.provider == "plugin" and not config.llm.class_path:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message="LLM plugin provider requires llm.class_path.",
                recommended_fix="Set llm.class_path to 'package.module:ClassName'.",
            )
        )


def _check_plugin(
    label: str,
    provider: str,
    class_path: str | None,
    diagnostics: list[ConfigDiagnostic],
) -> None:
    if provider != "plugin":
        return
    if not class_path:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"{label} plugin provider requires class_path.",
                recommended_fix=f"Set {label}.class_path to 'package.module:ClassName'.",
            )
        )
        return
    try:
        load_class(class_path)
    except ExtensionLoadError as exc:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"{label} plugin failed to load: {exc}",
                recommended_fix="Check the package is installed and the class path is correct.",
            )
        )


def _check_knowledge_root(root: Path, diagnostics: list[ConfigDiagnostic]) -> None:
    if not root.exists():
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"Knowledge pack root does not exist: {root}",
                recommended_fix="Create the directory or update knowledge.pack_root.",
            )
        )


def _check_artifact_root(
    root: Path,
    diagnostics: list[ConfigDiagnostic],
    *,
    create: bool,
) -> None:
    if root.exists():
        return
    try:
        if create:
            root.mkdir(parents=True, exist_ok=True)
        else:
            root.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"Artifact root cannot be created: {root} ({exc})",
                recommended_fix="Choose a writable artifact root.",
            )
        )


def _check_audit_path(path: Path, diagnostics: list[ConfigDiagnostic]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=f"Audit SQLite parent cannot be created: {path.parent} ({exc})",
                recommended_fix="Choose a writable audit.sqlite_path.",
            )
        )


def _check_private_artifacts(
    mode: str,
    artifact_root: Path,
    diagnostics: list[ConfigDiagnostic],
) -> None:
    if mode != "private-extension":
        return
    if artifact_root.resolve().is_relative_to(PROJECT_ROOT.resolve()):
        diagnostics.append(
            ConfigDiagnostic(
                severity="warning",
                message="private-extension mode is writing artifacts inside the public repo.",
                recommended_fix=(
                    "Set DREAM_ARTIFACT_ROOT to a private path outside the public checkout."
                ),
            )
        )


def _check_private_provider_approval(resolved, diagnostics: list[ConfigDiagnostic]) -> None:
    if resolved.mode != "private-extension":
        return
    try:
        ProviderEgressPolicy().require_approved(resolved)
    except ProviderConfigurationError as exc:
        diagnostics.append(
            ConfigDiagnostic(
                severity="error",
                message=str(exc),
                recommended_fix=(
                    "Set DREAM_LLM_APPROVAL_FILE to an unexpired exact provider/model/endpoint "
                    "approval outside the public checkout, or use the mock provider."
                ),
            )
        )


def _check_tracked_env(diagnostics: list[ConfigDiagnostic]) -> None:
    if not (PROJECT_ROOT / ".git").exists():
        return
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "ls-files", "--error-unmatch", ".env"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        diagnostics.append(
            ConfigDiagnostic(
                severity="warning",
                message=".env appears to be tracked by git.",
                recommended_fix=(
                    "Remove .env from git and keep only .env.example in the public repo."
                ),
            )
        )
