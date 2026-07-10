<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Architecture

![DREAM Qwen Cloud architecture](assets/qwencloud-architecture.svg)

Devpost upload asset: [`assets/qwencloud-architecture.png`](assets/qwencloud-architecture.png).
Regenerate it with `scripts/qwencloud-export-architecture-png.ps1`.

## Runtime Path

1. User opens the Angular Judge Arena or calls the FastAPI experience API.
2. Qwen receives the observation plus current active memory and returns a
   structured `remember`, `supersede`, `forget`, or `ignore` proposal.
3. DREAM validates the proposal and commits lifecycle state, TTL, provenance,
   and decision audit records to the experience repository.
4. Later sessions rank only active, unexpired memory into a hard token budget;
   feedback changes future ranking.
5. Requirement workflows combine recalled experience with approved source
   claims, knowledge packs, codebase evidence, and graph paths before calling
   `QwenCloudProvider` for an engineering artifact.
6. DREAM stores generated artifacts, context trails, scorecards, and human
   ratings for later retrieval and improvement.

## Deployment Path

The submission deployment target is Alibaba Cloud Function Compute in
`ap-southeast-1`, using an ACR-free Python 3.12 code package on
`custom.debian11`. Singapore matches the Model Studio dedicated workspace
region, shortening the cross-region network path and reducing timeout risk.
The runtime defaults to Model Studio's official Singapore shared endpoint after
the workspace-dedicated domain timed out in FC egress validation; local and
benchmark flows can continue using the dedicated workspace URL. Runtime secrets
and model settings are provided through environment variables:

- `DASHSCOPE_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_MODEL`
- `DREAM_CONFIG_FILE=examples/config/dream.qwen.yaml`

The public `/health` endpoint confirms provider, model, deployment target,
region, and proof file without exposing secrets.
