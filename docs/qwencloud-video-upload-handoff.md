<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Upload Handoff

Use this handoff when publishing the Devpost demo video to YouTube, Vimeo,
or Facebook Video. Devpost requires a public video URL; a local MP4
alone is not enough for final submission.

## Local Video File

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

Render or refresh it with:

```powershell
scripts/qwencloud-render-demo-video.ps1
scripts/qwencloud-video-publication-handoff.ps1
scripts/qwencloud-video-upload-status.ps1 -AllowDraft
```

The render command also writes `artifacts/qwencloud-proof/demo-video-render-*.md`
and `.json` manifests with the final MP4 duration, resolution, codec, SHA256,
and source asset hashes. Use the SHA256 to confirm the uploaded video came from
the reviewed local file.

The publication handoff command writes `video-publication-handoff-*.md` and
`.json` with the final upload title, description, tags, local MP4 SHA256, and
the exact action-time confirmation boundary before selecting the file in a
third-party upload page.

Expected metadata:

- Duration: under 3 minutes, target around 2:15 to 2:45.
- Resolution: at least 1280x720.
- Format: MP4/H.264.

## Custom Thumbnail

Use this optional 1280x720 thumbnail when the upload platform asks for a
custom cover image:

`docs/assets/qwencloud-video-thumbnail.png`

Refresh it from the source SVG with:

```powershell
scripts/qwencloud-export-video-thumbnail.ps1
```

The publication handoff includes the thumbnail path and SHA256 next to the MP4
hash, so the selected upload assets can be checked against the final bundle.

## Captions

Use this optional English subtitle file when the upload platform asks for
captions or subtitles:

`docs/qwencloud-demo-video-captions.srt`

The readable transcript lives at:

`docs/qwencloud-demo-video-transcript.md`

The publication handoff includes the caption file path and SHA256 next to the
MP4 and thumbnail hashes.

## Upload Target

Preferred platform: YouTube.

Acceptable Devpost public URL platforms:

- YouTube: `https://www.youtube.com/watch?v=...`
- YouTube short URL: `https://youtu.be/...`
- Vimeo: `https://vimeo.com/...`
- Facebook Video: `https://www.facebook.com/watch/?v=...`
- Facebook short link: `https://fb.watch/...`

Set visibility to public or another Devpost-accessible mode that does not
require a private login, password, or invitation.

Selecting the MP4, custom thumbnail, or caption file in the upload UI transmits
that local file to the chosen third-party video platform. Confirm the
account/channel and visibility at action time before selecting any file.

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
