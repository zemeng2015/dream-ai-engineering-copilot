<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud GitHub Release Workflow

Use the manual `Qwen Cloud Release` GitHub Actions workflow when local Alibaba
Cloud credentials or Docker registry state are easier to manage through GitHub
secrets than the desktop shell.

## Required GitHub Secrets

Add these repository secrets before running the workflow:

- `ALIBABA_CLOUD_ACCESS_KEY_ID`
- `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- `ALIBABA_CLOUD_REGION`
- `ALIBABA_CLOUD_CONTAINER_IMAGE`
- `ALIBABA_CONTAINER_REGISTRY_USERNAME`
- `ALIBABA_CONTAINER_REGISTRY_PASSWORD`
- `DASHSCOPE_API_KEY`

Optional:

- `ALIBABA_CLOUD_ACCOUNT_ID`
- `QWEN_BASE_URL`
- `QWEN_MODEL`

The workflow validates secret presence by name only and never writes secret
values into repo files.

Generate a local status report and placeholder template with:

```powershell
scripts/qwencloud-github-secrets-handoff.ps1 -AllowDraft
```

After setting same-named local environment variables, push them into repository
secrets with:

```powershell
scripts/qwencloud-github-secrets-handoff.ps1 -SetFromEnv
```

The script sends values through stdin to `gh secret set`; it does not write
secret values into its JSON or Markdown reports.

## Manual Run

1. Upload the demo MP4 using `docs/qwencloud-video-upload-handoff.md` to a
   public YouTube, Vimeo, Facebook Video, `fb.watch`, or Youku URL.
2. Open GitHub Actions, choose `Qwen Cloud Release`, and click `Run workflow`.
3. Paste the public demo video URL.
4. Leave `backendUrl` blank for a real deploy, or set it with `skipDeploy=true`
   if a Function Compute backend already exists.
5. Download the `qwencloud-release-proof` artifact after the workflow finishes.

The workflow runs:

- Python install and release script validation.
- Serverless Devs configuration from GitHub secrets.
- Docker login to Alibaba Container Registry.
- `scripts/qwencloud-alibaba-release.ps1`.
- Final readiness and final upload bundle generation.
- Final action board generation when local diagnostics are needed.
- Artifact upload for Devpost proof files and handoff files.

The Alibaba proof screenshot step uses headless Chrome/Chromium. GitHub-hosted
Ubuntu runners normally include Chrome; local/self-hosted runners must provide
Chrome, Chromium, Edge, or a compatible command on `PATH`.

## Final Gate

The release is complete only when the generated final readiness report says
`Ready for final Devpost submit: True`. A successful workflow run can still
produce a DRAFT bundle when public video, backend URL, Alibaba screenshot, or
proof recording evidence is missing.
