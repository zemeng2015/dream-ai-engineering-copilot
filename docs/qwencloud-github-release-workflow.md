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

The workflow sets `GH_TOKEN` from the GitHub-provided `github.token` so the
final CI proof, release summary, and artifact handoff checks can query the
current repository with `gh` without requiring a personal access token.
Its explicit token permissions are `contents: read` and `actions: read`, which
cover checkout plus workflow-run and artifact-proof queries.

You can keep values in an ignored local dotenv file:

```powershell
Copy-Item .env.qwencloud.local.example .env.qwencloud.local
# Fill .env.qwencloud.local locally.
scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv
```

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
secret values into its JSON or Markdown reports. `-EnvFile` imports values into
the current PowerShell process only.

## Manual Run

1. Upload the demo MP4 using `docs/qwencloud-video-upload-handoff.md` to a
   public YouTube, Vimeo, Facebook Video, or Youku URL.
2. Open GitHub Actions, choose `Qwen Cloud Release`, and click `Run workflow`.
3. Paste the public demo video URL.
4. Leave `backendUrl` blank for a real deploy, or set it with `skipDeploy=true`
   if a Function Compute backend already exists.
5. Ingest the `qwencloud-release-proof` artifact after the workflow finishes:

   ```powershell
   scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot
   ```

   Without `-RunId`, the ingest script selects the latest completed successful
   `Qwen Cloud Release` run and skips newer queued or in-progress runs.

   If the workflow run is marked failed because a final DRAFT gate tripped but
   the artifact upload step still completed, `-AllowDraft` selects the latest
   completed run. Add `-RunId` only when you need to force a specific failed run:

   ```powershell
   scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot -RunId "<run-id>" -AllowDraft
   ```

6. Open the workflow run summary and copy the Backend URL, `/qwencloud/showcase`
   proof path, final bundle zip path, and SHA256 from the `Qwen Cloud Release
   Summary` section.

The workflow runs:

- Python install and release script validation.
- Proof capture tooling setup: installs `ffmpeg`, validates `ffprobe`, and
  confirms Chrome/Chromium is available before deployment proof capture.
- Public demo video URL validation without requiring the local MP4 on the
  GitHub runner.
- Serverless Devs configuration from GitHub secrets.
- Docker login to Alibaba Container Registry.
- `scripts/qwencloud-alibaba-release.ps1`.
- Final readiness and final upload bundle generation.
- Final action board generation when local diagnostics are needed.
- Final upload bundle generation skips the GitHub secrets audit inside Actions,
  because the workflow has already validated required secrets from the current
  run environment and should not call `gh secret list`.
- `scripts/qwencloud-release-summary.ps1`, which writes the latest backend URL,
  showcase proof, final bundle hash, and remaining blockers to the GitHub job
  summary and artifact folder even when the run remains DRAFT.
- Artifact upload for Devpost proof files and handoff files.

The GitHub runner validates the public video URL but skips the local MP4 file
check in final readiness, because `artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`
is an ignored local upload artifact rather than a committed repo file.

The Alibaba proof screenshot step uses headless Chrome/Chromium. GitHub-hosted
Ubuntu runners normally include Chrome; local/self-hosted runners must provide
Chrome, Chromium, Edge, or a compatible command on `PATH`.

## Final Gate

The release is complete only when the generated final readiness report says
`Ready for final Devpost submit: True`. A successful workflow run can still
produce a DRAFT bundle when public video, backend URL, Alibaba screenshot, or
proof recording evidence is missing.
