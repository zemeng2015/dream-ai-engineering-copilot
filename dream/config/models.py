# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Mode = Literal["public-demo", "private-extension"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock", "openai-compatible", "qwen-cloud", "plugin"] = "mock"
    model: str | None = None
    base_url: str | None = None
    base_url_env: str | None = None
    api_key_env: str | None = None
    class_path: str | None = None


class KnowledgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_root: str | None = None
    pack_root_env: str | None = None


class ArtifactConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str | None = None
    root_env: str | None = None


class AuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sqlite_path: str | None = None
    sqlite_path_env: str | None = None


class RedactionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["default", "plugin"] = "default"
    class_path: str | None = None


class PromptPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["default", "plugin"] = "default"
    class_path: str | None = None


class DreamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Mode = "public-demo"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    redaction: RedactionConfig = Field(default_factory=RedactionConfig)
    prompt_policy: PromptPolicyConfig = Field(default_factory=PromptPolicyConfig)


class ResolvedLLMConfig(BaseModel):
    provider: str
    model: str | None
    base_url: str | None
    base_url_env: str | None
    api_key_env: str | None
    api_key_configured: bool
    class_path: str | None


class ResolvedPathConfig(BaseModel):
    root: Path
    source: str


class ResolvedAuditConfig(BaseModel):
    sqlite_path: Path
    source: str


class ResolvedProviderConfig(BaseModel):
    provider: str
    class_path: str | None


class ResolvedDreamConfig(BaseModel):
    mode: Mode
    source_file: Path | None
    llm: ResolvedLLMConfig
    knowledge: ResolvedPathConfig
    artifacts: ResolvedPathConfig
    audit: ResolvedAuditConfig
    redaction: ResolvedProviderConfig
    prompt_policy: ResolvedProviderConfig


class ConfigDiagnostic(BaseModel):
    severity: Literal["info", "warning", "error"]
    message: str
    recommended_fix: str | None = None


class ConfigValidationReport(BaseModel):
    ok: bool
    config: ResolvedDreamConfig
    diagnostics: list[ConfigDiagnostic] = Field(default_factory=list)
