<!-- SPDX-License-Identifier: Apache-2.0 -->

# Configuration

DREAM loads config from `dream.yaml` in the public checkout, or from the path in `DREAM_CONFIG_FILE`.

Minimal public demo config:

```yaml
mode: public-demo
llm:
  provider: mock
```

Qwen Cloud hackathon config:

```yaml
mode: public-demo
llm:
  provider: qwen-cloud
  model: qwen3.7-plus
  base_url_env: QWEN_BASE_URL
  api_key_env: DASHSCOPE_API_KEY
```

The default Qwen Cloud base URL is
`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, matching the hackathon
resource page. Production deployments can override `QWEN_BASE_URL` with a
workspace-specific Alibaba Cloud Model Studio endpoint.

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
