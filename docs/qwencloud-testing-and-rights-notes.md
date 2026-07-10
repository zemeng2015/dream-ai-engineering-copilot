<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Testing and Rights Notes

Use this as the judge-facing testing and compliance note for the Devpost
submission packet.

## Working Project Access

Primary testing URL:

```text
<paste Alibaba Function Compute backend URL>
```

After deployment, the URL must stay reachable and free to access through the
hackathon judging period. The expected public checks are:

```powershell
Invoke-RestMethod "https://<function-compute-endpoint>/health"
scripts/qwencloud-hackathon-verify.ps1 -BaseUrl "https://<function-compute-endpoint>"
scripts/qwencloud-hackathon-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

The `/health` response should prove:

- `track`: `Track 1: MemoryAgent`
- `llm_provider`: `qwen-cloud`
- `deployment_target`: `Alibaba Cloud Function Compute`
- `proof_file`: `deploy/alibaba/serverless-devs-runtime.yaml`

## Local Reproduction

```powershell
git clone https://github.com/zemeng2015/dream-ai-engineering-copilot.git
cd dream-ai-engineering-copilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<judge-provided-or-owner-configured-key>"
$env:QWEN_BASE_URL="https://<workspace-id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
uvicorn dream.api.app:app --host 127.0.0.1 --port 8000
scripts/qwencloud-hackathon-verify.ps1 -BaseUrl http://127.0.0.1:8000
```

Linux/macOS judges can run the isolated Bash proof runner without opening a
second terminal:

```bash
git clone https://github.com/zemeng2015/dream-ai-engineering-copilot.git
cd dream-ai-engineering-copilot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
bash scripts/qwencloud-run-local-proof.sh --skip-draft
```

## Rights and Asset Notes

- Source code is published under Apache-2.0 in the root `LICENSE`.
- Qwen Cloud and Alibaba Cloud names are used only to identify required
  hackathon platforms and deployment targets.
- The architecture diagram is generated from repo-owned Mermaid source in
  `docs/assets/qwencloud-architecture.svg`.
- The demo video and Alibaba proof video are rendered by repo scripts from
  repo-owned text, screenshots, and runtime proof data.
- Do not add copyrighted music, third-party logos, stock images, or unrelated
  trademarks to the Devpost video or uploaded screenshots.
- Public proof endpoints expose provider, track, region, and proof-file status
  only. They must not expose API keys, access keys, tokens, or private user data.

## Final Submit Guard

Before final Devpost submit, run:

```powershell
scripts/qwencloud-official-rules-gate.ps1 `
  -DemoVideoUrl "https://www.youtube.com/..." `
  -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-final-readiness.ps1 `
  -EnvFile .env.qwencloud.local `
  -DemoVideoUrl "https://www.youtube.com/..." `
  -BackendUrl "https://<function-compute-endpoint>"
```

Both scripts must report `READY` before final submission.
