<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Architecture

![DREAM Qwen Cloud architecture](assets/qwencloud-architecture.svg)

Devpost upload asset: [`assets/qwencloud-architecture.png`](assets/qwencloud-architecture.png).
Regenerate it with `scripts/qwencloud-export-architecture-png.ps1`.

## Runtime Path

1. User opens the Angular workbench or calls the FastAPI API.
2. DREAM retrieves durable memory from knowledge packs, codebase indexes,
   approved memory claims, evidence graphs, and audit/eval history.
3. The prompt is assembled with compact source-backed context and sent through
   `QwenCloudProvider`.
4. Qwen Cloud returns the generated engineering output.
5. DREAM stores audit records, generated artifacts, scorecards, and human
   ratings for later retrieval and improvement.

## Deployment Path

The backend container runs on Alibaba Cloud Function Compute. Runtime secrets
are provided through environment variables:

- `DASHSCOPE_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_MODEL`
- `DREAM_CONFIG_FILE=examples/config/dream.qwen.yaml`

The public `/health` endpoint confirms provider, model, deployment target,
region, and proof file without exposing secrets.
