# DREAM submission video V3

This directory contains the isolated, reproducible pipeline for the 150-second
Qwen Cloud hackathon demo. It does not modify the DREAM product runtime or
replace the public video.

## What It Proves

- Fresh browser capture runs the public Alibaba Function Compute Judge Arena.
- Capture metadata locks the video to `qwen-cloud`, `qwen3.7-plus`, Tablestore,
  the live FC instance, and exact build `cb6255b`.
- Three five-second clips preserve the continuous remember, supersede, and
  recall interaction before each readable evidence frame.
- Alibaba Model Studio `qwen3-tts-instruct-flash-2026-01-26` produces ten
  instruction-controlled founder-style narration clips.
- The video shows cross-instance durability, the 20/20 public contention proof,
  transparent benchmark limitations, and the deployed Alibaba architecture.
- Validation checks evidence, narration provenance, privacy, codec, duration,
  loudness, black frames, breathing room, and final SHA256.

Generated capture and narration files live in `public/generated/`. Rendered
intermediates live in `out/`. Both are intentionally ignored by Git.

## Install

```powershell
npm ci
```

## Render

To refresh the live capture and Qwen narration, render, master, and validate:

```powershell
.\render-v3.ps1 -EnvFile "<path-to-.env.qwencloud.local>"
```

To reuse the reviewed capture and narration while iterating on visuals:

```powershell
.\render-v3.ps1 -SkipCapture -SkipNarration
```

The canonical repository wrapper is:

```powershell
..\..\scripts\qwencloud-render-demo-video.ps1
```

## Development Checks

```powershell
npx tsc --noEmit
npm run preview:v3
npm run validate:v3
npm run render:v3
```

The local candidate is written under
`artifacts/qwencloud-proof/video-v3/`. Public upload and Devpost replacement
remain explicit user-confirmed actions.
