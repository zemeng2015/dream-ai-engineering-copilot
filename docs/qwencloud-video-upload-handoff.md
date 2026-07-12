<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Upload Handoff

Use this handoff when publishing the Devpost demo video to YouTube, Vimeo,
Facebook Video, or Youku. Devpost requires a public video URL; a local MP4
alone is not enough for final submission.

## Local Video File

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

Render or refresh it with:

```powershell
scripts/qwencloud-render-demo-video.ps1
scripts/qwencloud-video-publication-handoff.ps1
scripts/qwencloud-video-upload-status.ps1 -AllowDraft
```

The render command also writes a V3 validation JSON, contact sheet, narration
manifest, capture manifest, and 12 QA frames under
`artifacts/qwencloud-proof/video-v3/`. Use the SHA256 in the validation JSON to
confirm the uploaded video came from the reviewed local file.

The publication handoff command writes `video-publication-handoff-*.md` and
`.json` with the final upload title, description, tags, local MP4 SHA256, and
the exact action-time confirmation boundary before selecting the file in a
third-party upload page.

Expected metadata:

- Duration: 2:30 and under the 3-minute limit.
- Resolution: 1920x1080.
- Format: MP4/H.264 with 48 kHz stereo AAC.
- Story: stale-rollout hook, continuous `remember -> supersede -> 19/64-token
  recall`, cross-instance Tablestore durability, 20/20 public contention,
  transparent synthetic measurement, and verified Alibaba architecture.

## Custom Thumbnail

Use this optional 1280x720 thumbnail when the upload platform asks for a
custom cover image:

`artifacts/qwencloud-proof/video-v3/dream-v3-thumbnail.png`

Refresh it from the source SVG with:

```powershell
cd tools/submission-video-v2
npm run gallery:v3
```

The publication handoff includes the thumbnail path and SHA256 next to the MP4
hash, so the selected upload assets can be checked against the final bundle.

The same command writes the four reviewed 1800x1200 Devpost gallery images to
`artifacts/qwencloud-proof/video-v3/devpost-gallery-v3/` with a SHA256 manifest.

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
- Youku: `https://v.youku.com/v_show/id_...`

Note: the public overview currently names YouTube, Vimeo, and Facebook Video,
while the Official Rules page names YouTube, Vimeo, and Youku. The local
validator accepts the union, but YouTube or Vimeo remain the least ambiguous
choices for final submission.

Set visibility to public or another Devpost-accessible mode that does not
require a private login, password, or invitation.

Selecting the MP4, custom thumbnail, or caption file in the upload UI transmits
that local file to the chosen third-party video platform. Confirm the
account/channel and visibility at action time before selecting any file.

## Copy Fields

Title:

```text
DREAM MemoryAgent: One Current Truth Across Qwen Sessions | Qwen Cloud
```

Description:

```text
DREAM is a Qwen Cloud Track 1 MemoryAgent that prevents stale cross-session guidance from quietly returning. Qwen understands whether experience should be remembered or superseded; DREAM and Alibaba Tablestore enforce one current, reviewable truth under a hard context budget.

The public Singapore Function Compute build shows real Qwen receipts, durable recall after an FC instance replacement, and 20/20 successful conflicting writes with one active truth and 19 historical versions. The video also reports a transparently limited seven-case synthetic comparison: the same qwen3.7-plus model improved from 25.3 to 48.7 with DREAM (+23.4, 7/7 wins; Recall@12 remains 35.6%).

Live demo: https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/hackathon-demo

Repo: https://github.com/zemeng2015/dream-ai-engineering-copilot/tree/codex/champion-memory-loop
Track: Track 1: MemoryAgent
```

Optional tags:

```text
Qwen Cloud, Alibaba Cloud, MemoryAgent, Tablestore, Function Compute, governed AI memory, hackathon
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

scripts/qwencloud-alibaba-runtime-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"

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
