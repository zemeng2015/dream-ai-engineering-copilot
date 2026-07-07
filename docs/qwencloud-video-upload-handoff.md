<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Upload Handoff

Use this handoff when publishing the Devpost demo video to YouTube, Vimeo,
or Youku. Devpost requires a public video URL; a local MP4
alone is not enough for final submission.

## Local Video File

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

Render or refresh it with:

```powershell
scripts/qwencloud-render-demo-video.ps1
scripts/qwencloud-video-upload-status.ps1 -AllowDraft
```

Expected metadata:

- Duration: under 3 minutes.
- Resolution: at least 1280x720.
- Format: MP4/H.264.

## Upload Target

Preferred platform: YouTube.

Acceptable Devpost public URL platforms:

- YouTube: `https://www.youtube.com/watch?v=...`
- YouTube short URL: `https://youtu.be/...`
- Vimeo: `https://vimeo.com/...`
- Youku: `https://v.youku.com/...`

Set visibility to public or another Devpost-accessible mode that does not
require a private login, password, or invitation.

## Copy Fields

Title:

```text
DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence
```

Description:

```text
DREAM is a Qwen Cloud Track 1 MemoryAgent for source-backed engineering intelligence. It uses persistent, governed engineering memory, Qwen Cloud generation, and Alibaba Cloud deployment proof to turn codebase docs, incidents, and review context into auditable requirement and review outputs.

Repo: https://github.com/zemeng2015/dream-ai-engineering-copilot
Track: Track 1: MemoryAgent
```

Optional tags:

```text
Qwen Cloud, Alibaba Cloud, MemoryAgent, AI engineering, source-backed memory, hackathon
```

## Chrome Upload Troubleshooting

If uploading through Codex-controlled Chrome fails with a file chooser error
such as `Not allowed`, enable Chrome extension file access first:

```text
To enable file upload, go to chrome://extensions in Chrome, click Details under the Codex extension, and enable "Allow access to file URLs." See https://developers.openai.com/codex/app/chrome-extension#upload-files for details.
```

After enabling that setting, reopen YouTube Studio, choose the MP4 above, and
continue the upload. If browser automation is still blocked, upload the same MP4
manually from the signed-in browser.

## After Upload

Open the final video page in a private/incognito browser window or logged-out
browser session and confirm it plays.

Then pass the public URL into the release and final readiness commands:

```powershell
scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"

scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"

scripts/qwencloud-hackathon-submission-packet.ps1 `
  -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" `
  -DemoVideoUrl "<public-video-url>" `
  -BackendUrl "<deployed-url>"

scripts/qwencloud-final-readiness.ps1 `
  -EnvFile .env.qwencloud.local `
  -DemoVideoUrl "<public-video-url>" `
  -BackendUrl "<deployed-url>"

scripts/qwencloud-final-upload-bundle.ps1 `
  -EnvFile .env.qwencloud.local `
  -DemoVideoUrl "<public-video-url>" `
  -BackendUrl "<deployed-url>"
```

For GitHub Actions or other environments that only need to validate the public
video page and do not have the local MP4 artifact, use:

```powershell
scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>" -SkipLocalVideoChecks
```

The final packet and readiness dashboard must report `READY` before Devpost is
submitted.
