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

Legacy Qwen Cloud keys can use the generic international DashScope endpoint. New
Model Studio keys beginning with `sk-ws` must set `QWEN_BASE_URL` to the dedicated
OpenAI-compatible workspace URL shown on the Singapore API Key page, for example
`https://<workspace-id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`.

Private extension config:

```yaml
mode: private-extension
llm:
  provider: openai-compatible
  model: gpt-5.4
  base_url: "https://api.openai.com/v1"
  api_key_env: PILOT_OPENAI_API_KEY
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

Private mode also requires an absolute `DREAM_LLM_APPROVAL_FILE` path outside
the public checkout. The JSON manifest must use schema
`provider-approval-v1` and exactly match provider, base URL, and model, with a
timezone-aware approval and expiration window. See
[Provider Egress Foundation](provider-egress-foundation.md).

Commands:

```bash
dream config show
dream config validate
dream config doctor
```

`config show` prints resolved paths and provider names without secret values. API keys are referenced only by environment variable name and presence.
