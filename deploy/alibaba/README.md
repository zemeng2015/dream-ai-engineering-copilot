<!-- SPDX-License-Identifier: Apache-2.0 -->

# Alibaba Cloud Deployment Proof

This folder is the Devpost proof path for running DREAM as a Qwen Cloud
MemoryAgent on Alibaba Cloud Function Compute.

The primary hackathon path is the ACR-free custom runtime deployment in
`serverless-devs-runtime.yaml`. It targets Function Compute in
`ap-southeast-1` with a Python 3.12 code package on `custom.debian11`, and does
not require Alibaba Container Registry. Singapore is selected to match the
Model Studio dedicated workspace region, shortening the cross-region network
path and reducing timeout risk. The FC template uses Model Studio's official
Singapore shared endpoint by default because the workspace-dedicated domain
timed out during FC egress validation. The public runtime does not expose an
endpoint override that could redirect its bearer token.
The existing `serverless-devs.yaml`
custom-container template remains as a fallback when an ACR repository is
already available.

The anonymous judge demo is deliberately bounded: Function Compute uses a
function-level reserved concurrency cap of `1` with per-instance concurrency
`4`, Qwen prompts are capped at `24,000` characters, completions at `1,200`
tokens, and each runtime process accepts at most `6` Qwen-backed API requests
per minute. These are hackathon cost-abuse controls, not a substitute for
production authentication or a shared distributed rate limiter.

Function code remains immutable under `/code`; disposable artifacts and the
legacy audit ledger use `/tmp`. Experience memory is stored durably in the
`dreammem` Tablestore instance and `dream_experience_v1` table. The table uses
`scope_id` and `record_id` string primary keys, permanent TTL, one cell version,
zero reserved read/write CUs, and partition-scoped local transactions. A
single transaction atomically supersedes the previous fact, writes the new
fact, and appends the decision receipt.

Function Compute assumes `dream-qwencloud-fc-role`. FC injects temporary role
credentials into the runtime; no long-lived Alibaba AccessKey is copied into
the function configuration. The role is limited to the six Tablestore data and
transaction operations declared under `ram/` for this one table.

## Required Environment

Preferred local handoff:

```powershell
Copy-Item .env.qwencloud.local.example .env.qwencloud.local
# Fill .env.qwencloud.local locally. It is ignored by git.
scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft
scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer
```

Equivalent explicit environment variables:

```powershell
$env:ALIBABA_CLOUD_RUNTIME_REGION="ap-southeast-1"
$env:ALIBABA_CLOUD_ACCOUNT_ID="<account-id>"
$env:DASHSCOPE_API_KEY="<qwen-cloud-api-key>"
$env:QWEN_BASE_URL="https://<workspace-id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen3.7-plus"
```

The deployed storage resources are:

```text
Region:       ap-southeast-1
Instance:     dreammem (CU mode, high-performance, ZRS)
Table:        dream_experience_v1
Primary key:  scope_id STRING, record_id STRING
Throughput:   0 reserved read CUs, 0 reserved write CUs
Transaction:  local transaction enabled
```

For a Model Studio key beginning with `sk-ws`, copy the dedicated workspace URL
from the Singapore API Key page for local validation. Model Studio also permits
same-region workspace keys on the official shared Singapore domain used by the
FC template.

## Build And Deploy

ACR-free custom runtime path:

```powershell
scripts/qwencloud-release-config-audit.ps1 -EnvFile .env.qwencloud.local -UseCodePackage
scripts/qwencloud-build-fc-code-package.ps1
s deploy -t deploy/alibaba/serverless-devs-runtime.yaml -y
```

Or run the complete local release flow:

```powershell
scripts/qwencloud-alibaba-runtime-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..."
```

Custom-container fallback:

Run a deploy preflight first. It checks required files, Docker, Serverless Devs,
required environment variables, and optionally builds and smokes the container
locally.

```powershell
scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft
scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer
```

The credentials handoff writes a local placeholder template under
`artifacts/qwencloud-proof/` with the exact environment variables, `s config add`
command, registry login command, and final release commands. It does not write
real secrets.

To run the complete release path in one command after environment variables,
Serverless Devs access, and registry login are configured:

```powershell
scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..."
```

Alternatively, configure the repository secrets listed in
`docs/qwencloud-github-release-workflow.md` and run the manual GitHub Actions
workflow named `Qwen Cloud Release`.

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
proof file path. It also exposes the non-secret storage backend, transaction
mode, build SHA, and FC instance ID, but never exposes API keys or role tokens.

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

Render the separate Alibaba backend proof recording:

```powershell
scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

The proof recording is written to
`artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`.

Validate that the screenshot, proof recording, and captured health metadata all
come from the same Alibaba Cloud backend:

```powershell
scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "https://<function-compute-endpoint>"
```
