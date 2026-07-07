<!-- SPDX-License-Identifier: Apache-2.0 -->

# Publish Playbook (Final Submission Day)

## Recommended assets

- Video file name: `DREAM-Qwen-Cloud-MemoryAgent-Demo.mp4`
- Video length target: `2:45` to `3:00`
- Architecture file: `docs/assets/qwencloud-architecture.svg` (also include PNG export if preferred for Devpost upload)
- Demo proof file: `deploy/alibaba/serverless-devs.yaml`

## Command bundle

```powershell
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<key>"
$env:QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/requirements/draft -H "Content-Type: application/json" -d '{"team_id":"demo_team","rough_business_request":"Users need to know why a forecast job is stuck running","llm_provider":"qwen-cloud"}'
```

```powershell
scripts/qwencloud-hackathon-smoke.ps1
scripts/qwencloud-hackathon-verify.ps1
scripts/qwencloud-hackathon-proof.ps1
```

`qwencloud-hackathon-proof.ps1` writes timestamped JSON artifacts in
`artifacts/qwencloud-proof/` with both `/health` and `/requirements/draft`
proof payloads for judge-facing evidence.

## Devpost fill order

1. Title: `DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`
2. Track: `Track 1: MemoryAgent`
3. Description: copy from `docs/qwencloud-devpost-form-fields.md`
4. Add repo link and Apache-2.0 link
5. Upload architecture image
6. Upload video (link if supported by platform)
7. Add deployment proof section with `deploy/alibaba/serverless-devs.yaml` and `deploy/alibaba/README.md`
8. Submit and immediately open public project page to confirm links are visible
