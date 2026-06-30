<!-- SPDX-License-Identifier: Apache-2.0 -->

# Configuration

DREAM loads config from `dream.yaml` in the public checkout, or from the path in `DREAM_CONFIG_FILE`.

Minimal public demo config:

```yaml
mode: public-demo
llm:
  provider: mock
```

Private extension config:

```yaml
mode: private-extension
llm:
  provider: plugin
  class_path: "private_plugins.custom_llm_provider:CustomLLMProvider"
knowledge:
  pack_root: "knowledge_packs"
artifacts:
  root_env: DREAM_ARTIFACT_ROOT
audit:
  sqlite_path_env: DREAM_AUDIT_SQLITE_PATH
redaction:
  provider: plugin
  class_path: "private_plugins.custom_redaction_provider:CustomRedactionProvider"
prompt_policy:
  provider: plugin
  class_path: "private_plugins.custom_prompt_policy:CustomPromptPolicy"
```

Commands:

```bash
dream config show
dream config validate
dream config doctor
```

`config show` prints resolved paths and provider names without secret values. API keys are referenced only by environment variable name and presence.
