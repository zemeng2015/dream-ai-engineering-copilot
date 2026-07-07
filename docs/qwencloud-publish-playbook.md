<!-- SPDX-License-Identifier: Apache-2.0 -->

# Publish Playbook (Final Submission Day)

## Recommended assets

- Video file name: `DREAM-Qwen-Cloud-MemoryAgent-Demo.mp4`
- Video length target: `2:45` to `3:00`
- Video upload handoff: `docs/qwencloud-video-upload-handoff.md`
- Architecture file: `docs/assets/qwencloud-architecture.png` for Devpost upload
- Alibaba proof screenshot: `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`
- Alibaba proof recording: `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`
- Source architecture SVG: `docs/assets/qwencloud-architecture.svg`
- Demo proof file: `deploy/alibaba/serverless-devs.yaml`
- Blog/social draft: `docs/qwencloud-build-journey-post.md`

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
scripts/qwencloud-run-local-proof.ps1
scripts/qwencloud-export-architecture-png.ps1
scripts/qwencloud-cloud-credentials-handoff.ps1 -AllowDraft
scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer
scripts/qwencloud-alibaba-release.ps1 -DemoVideoUrl "https://www.youtube.com/..."
scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"
scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "https://<function-compute-endpoint>"
scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-hackathon-verify.ps1
scripts/qwencloud-hackathon-proof.ps1
scripts/qwencloud-hackathon-submit-gate.ps1
scripts/qwencloud-hackathon-audit.ps1
scripts/qwencloud-devpost-handoff.ps1 -AllowDraft
scripts/qwencloud-hackathon-submission-packet.ps1 -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-final-readiness.ps1 -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-finalize-after-urls.ps1 -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-final-upload-bundle.ps1 -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-final-action-board.ps1 -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>" -AllowDraft
```

`qwencloud-hackathon-proof.ps1` writes timestamped JSON artifacts in
`artifacts/qwencloud-proof/` with both `/health` and `/requirements/draft`
proof payloads for judge-facing evidence.

`qwencloud-hackathon-submit-gate.ps1` performs the same proof collection with
strict checks for Track 1, qwen-cloud provider, expected proof file, and
requirement-draft success (unless `-SkipDraft` is set).

`qwencloud-hackathon-audit.ps1` adds a one-command pre-submit checklist:
repo/docs presence, public repo license visibility checks, and endpoint checks.

`qwencloud-run-local-proof.ps1` starts an isolated local Qwen-mode API,
waits for hackathon `/health` proof, runs verify/proof/submit gate/audit, and
then stops the API process.

Use `-AllowDirty` only while developing local changes; omit it for the final
pre-submit proof so the audit enforces a clean pushed worktree.

`qwencloud-deploy-preflight.ps1` checks Alibaba deploy readiness, Docker build,
and local container smoke before the image is pushed to Container Registry.

`qwencloud-alibaba-release.ps1` orchestrates the release path: preflight,
Docker tag/push, Serverless Devs deploy, backend verification, Alibaba proof
screenshot, proof recording, and final Devpost packet generation.

`qwencloud-capture-alibaba-proof.ps1` verifies the deployed `/health` response
and renders the Devpost-required Alibaba deployment screenshot.

`qwencloud-render-alibaba-proof-video.ps1` verifies the same backend proof and
renders a separate short Alibaba deployment proof recording.

`qwencloud-validate-alibaba-proof.ps1` checks the latest Alibaba capture JSON,
deployment screenshot, proof recording, and backend URL for one consistent
Alibaba Cloud Function Compute evidence chain.

`qwencloud-export-architecture-png.ps1` regenerates the Devpost-friendly PNG
architecture upload asset from the source SVG.

`qwencloud-hackathon-submission-packet.ps1` validates final public URLs,
architecture PNG dimensions, local demo video duration/resolution, backend
health proof, Alibaba screenshot/video readiness, and copy/paste Devpost text.

`qwencloud-final-readiness.ps1` is the final submit dashboard. It checks clean
git state, remote sync, latest CI, local tools, cloud env, Serverless Devs,
Alibaba proof integrity, artifact readiness, and final Devpost packet readiness.

`qwencloud-final-upload-bundle.ps1` creates a local zip containing upload
assets, the generated Devpost packet, and a manifest so the final submission
files are all in one place. It also includes the latest deploy preflight report,
Docker build/run logs, and final action board when available.

`qwencloud-final-action-board.ps1` runs video URL, cloud credential, GitHub
secret, and final readiness checks, then emits one Markdown board with the next
remaining action and whether Zack/action-time confirmation is required.

`qwencloud-finalize-after-urls.ps1` is the final one-command gate after the
public video and deployed backend URLs are known. It runs the submission packet,
final readiness dashboard, final upload bundle, and then writes a single final
status report.

`qwencloud-devpost-handoff.ps1` generates a local Markdown/HTML/JSON handoff
with official requirement coverage, copy fields, blockers, upload paths, and
next commands for the final Devpost form.

Use `docs/qwencloud-video-upload-handoff.md` for the public video upload title,
description, accepted platforms, visibility check, and Chrome file-access
troubleshooting.

## Devpost fill order

1. Title: `DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`
2. Track: `Track 1: MemoryAgent`
3. Description: copy from `docs/qwencloud-devpost-form-fields.md`
4. Add repo link and Apache-2.0 link
5. Upload architecture image
6. Upload Alibaba deployment screenshot
7. Upload or link Alibaba backend proof recording if Devpost requests it
8. Upload demo video link after verifying the public video page plays
9. Generate the final submission packet and copy testing instructions
10. Run final readiness and confirm `READY`
11. Create the final upload bundle and open the generated `devpost-handoff-*.html`
12. Add deployment proof section with `deploy/alibaba/serverless-devs.yaml` and `deploy/alibaba/README.md`
13. Add optional build journey link if published
14. Submit and immediately open public project page to confirm links are visible
