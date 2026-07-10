<!-- SPDX-License-Identifier: Apache-2.0 -->

# Build Journey Draft: DREAM on Qwen Cloud

Use this as the optional public blog or social post link for the Qwen Cloud
Hackathon bonus. Replace the placeholders after deployment and video upload.

## Short Social Post

I built DREAM for the Qwen Cloud Hackathon as a Track 1 MemoryAgent for
source-backed engineering intelligence.

The idea is simple: engineering teams do not just need another chatbot. They
need an agent that remembers source truth across docs, code, incidents,
runbooks, Jira history, PR reviews, and human-approved memory claims.

DREAM uses Qwen Cloud through an OpenAI-compatible provider, then wraps
generation with deterministic retrieval, memory governance, audit logs,
scorecards, and human review. The backend is packaged for Alibaba Cloud Function
Compute as an ACR-free custom runtime code package, with reproducible release
checks and public architecture proof.

Repo: https://github.com/zemeng2015/dream-ai-engineering-copilot
Demo video: <public video URL>
Backend proof: <deployed /health URL>

#QwenCloud #AIHackathon #MemoryAgent #AlibabaCloud #DeveloperTools #AIEngineering

## Long Blog Draft

# Building DREAM: A Qwen Cloud MemoryAgent for Engineering Teams

For the Qwen Cloud Hackathon, I built DREAM as a Track 1 MemoryAgent focused on
a real engineering problem: teams lose context faster than they lose code.

Requirements live in tickets. Architecture lives in docs. Operational truth
lives in runbooks and incidents. Review rules live in old pull requests. Tests
and code hold another layer of reality. When an AI assistant only sees a fresh
prompt, it can sound fluent while missing the source-backed context that makes
engineering decisions reliable.

DREAM treats that context as governed memory.

## What DREAM Does

DREAM loads and indexes engineering knowledge sources such as:

- runbooks and architecture docs
- incident history
- historical Jira and pull request notes
- codebase files, symbols, concepts, and tests
- approved memory claims and conflict records

That memory is then used by workflow agents for requirement drafting, impact
mapping, PR review assistance, context assembly, and evaluation.

The important design choice is that memory is not magic prompt stuffing. DREAM
keeps evidence visible. Memory can be promoted, rejected, reviewed, audited, and
evaluated. Generated outputs are tied back to source paths and run records so a
human reviewer can inspect why the agent said what it said.

## Where Qwen Cloud Fits

For the hackathon build, I added a first-class `qwen-cloud` provider that uses
Qwen Cloud through the OpenAI-compatible API. DREAM can run with deterministic
local behavior for tests and demos, then switch to Qwen-backed generation with:

```powershell
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<qwen-cloud-key>"
$env:QWEN_BASE_URL="https://<workspace-id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
uvicorn dream.api.app:app --host 127.0.0.1 --port 8000
```

The public `/health` endpoint reports Track 1, `qwen-cloud`, model, deployment
target, region, and the Alibaba Cloud proof file path without exposing secrets.

## Deployment Proof

The backend is packaged for Alibaba Cloud Function Compute as an ACR-free
Python 3.12 code package on `custom.debian11`. The repo includes:

- `deploy/alibaba/serverless-devs-runtime.yaml`
- `deploy/alibaba/README.md`
- `scripts/qwencloud-deploy-preflight.ps1`
- `scripts/qwencloud-hackathon-submit-gate.ps1`

The release audit checks local files, Serverless Devs config, required
environment variables, the Linux code package, and a local runtime smoke test
before the package is uploaded directly to Function Compute.

## What I Learned

The biggest lesson from this build is that agent memory needs product-level
controls, not just model-level intelligence. For engineering workflows, useful
memory must be:

- source-backed
- reviewable
- conflict-aware
- auditable
- small enough to fit into constrained context windows
- safe to run in public demo mode without leaking secrets

Qwen Cloud provides the reasoning layer. DREAM provides the memory governance
and engineering workflow shell around it.

## Links

- Repository: https://github.com/zemeng2015/dream-ai-engineering-copilot
- Architecture: https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/docs/assets/qwencloud-architecture.svg
- Architecture PNG: https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/docs/assets/qwencloud-architecture.png
- Deployment proof: https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/deploy/alibaba/serverless-devs-runtime.yaml
- Demo video: <public video URL>
- Live backend: https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/
