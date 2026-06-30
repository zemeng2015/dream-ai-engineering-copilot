<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plugin Development

DREAM loads plugin classes from config using:

```yaml
class_path: "some_package.some_module:SomeProvider"
```

Plugin classes should be importable in the Python environment where `dream` runs. Keep constructors simple; no-argument constructors are the most portable.

Supported extension points:

- `LLMProvider`
- `KnowledgePackProvider`
- `ArtifactStore`
- `RedactionProvider`
- `PromptPolicyProvider`
- `CodebaseMemoryProvider`
- `AuditSink`

Before using a private plugin, run:

```bash
dream config validate
dream config doctor
pytest tests/contracts
```

Provider outputs must not expose secret values in returned text, metadata, diagnostics, or audit fields.
