<!-- SPDX-License-Identifier: Apache-2.0 -->

# Alibaba Cloud Deployment Proof

This folder is the Devpost proof path for running DREAM as a Qwen Cloud
MemoryAgent on Alibaba Cloud Function Compute using a custom container.

## Required Environment

```powershell
$env:ALIBABA_CLOUD_REGION="ap-southeast-1"
$env:ALIBABA_CLOUD_CONTAINER_IMAGE="<registry>/<namespace>/dream-qwencloud-memoryagent:latest"
$env:DASHSCOPE_API_KEY="<qwen-cloud-api-key>"
$env:QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen3.7-plus"
```

## Build And Deploy

Run a deploy preflight first. It checks required files, Docker, Serverless Devs,
required environment variables, and optionally builds and smokes the container
locally.

```powershell
scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer
```

```powershell
docker build -t dream-qwencloud-memoryagent:latest .
docker tag dream-qwencloud-memoryagent:latest $env:ALIBABA_CLOUD_CONTAINER_IMAGE
docker push $env:ALIBABA_CLOUD_CONTAINER_IMAGE
s deploy -t deploy/alibaba/serverless-devs.yaml -y
```

After deployment, verify:

```powershell
curl https://<function-compute-endpoint>/health
curl -X POST https://<function-compute-endpoint>/requirements/draft `
  -H "Content-Type: application/json" `
  -d '{"team_id":"demo_team","rough_business_request":"Users need to know why a forecast job is stuck running","llm_provider":"qwen-cloud"}'
```

The `/health` payload intentionally exposes provider, model, region, and this
proof file path, but never exposes API keys.

Validate the deployed endpoint quickly:

```powershell
scripts/qwencloud-hackathon-verify.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

Generate the Devpost-required Alibaba deployment screenshot:

```powershell
scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

The screenshot is written to
`artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`.
