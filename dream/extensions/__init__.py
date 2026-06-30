# SPDX-License-Identifier: Apache-2.0

from dream.extensions.errors import ExtensionError, ExtensionLoadError
from dream.extensions.loader import load_class, load_instance
from dream.extensions.models import (
    ArtifactStore,
    AuditSink,
    CodebaseMemoryProvider,
    KnowledgePackProvider,
    LLMProvider,
    PromptPolicyProvider,
    RedactionProvider,
)
from dream.extensions.registry import (
    DefaultPromptPolicyProvider,
    DefaultRedactionProvider,
    LocalArtifactStore,
    LocalKnowledgePackProvider,
    NativeCodebaseMemoryProvider,
    SQLiteAuditSink,
    build_llm_provider,
    build_prompt_policy_provider,
    build_redaction_provider,
)

__all__ = [
    "ArtifactStore",
    "AuditSink",
    "CodebaseMemoryProvider",
    "DefaultPromptPolicyProvider",
    "DefaultRedactionProvider",
    "ExtensionError",
    "ExtensionLoadError",
    "KnowledgePackProvider",
    "LLMProvider",
    "LocalArtifactStore",
    "LocalKnowledgePackProvider",
    "NativeCodebaseMemoryProvider",
    "PromptPolicyProvider",
    "RedactionProvider",
    "SQLiteAuditSink",
    "build_llm_provider",
    "build_prompt_policy_provider",
    "build_redaction_provider",
    "load_class",
    "load_instance",
]
