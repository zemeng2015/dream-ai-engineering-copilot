<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Hackathon Official Requirements Snapshot

Checked date: 2026-07-07

Source URL: `https://qwencloud-hackathon.devpost.com/`

This snapshot records the public Devpost requirements used by the local
readiness gates. Re-check the source URL before final submit.

## Deadline

- Public Devpost page deadline: July 9, 2026 at 2:00pm PDT.
- Equivalent deadline used by local scripts: `2026-07-09T21:00:00Z`.

## Selected Track

- DREAM is submitted for Track 1: MemoryAgent.
- Track 1 expects persistent memory, memory storage/retrieval, forgetting stale
  information, and recalling critical memories within limited context windows.

## Required Submission Evidence

- Public open-source code repository with source code, assets, instructions,
  and detectable license.
- Proof of Alibaba Cloud deployment, including a short recording separate from
  the demo video and a repository file showing Alibaba Cloud service/API usage.
- Architecture diagram showing the system and Qwen Cloud/backend connections.
- Public demo video uploaded to an accepted public video platform. The public
  overview names YouTube, Vimeo, or Facebook Video; the Official Rules page
  names YouTube, Vimeo, or Youku. Local gates accept the union and recommend
  YouTube or Vimeo as the least ambiguous final choice.
- Text description explaining project features and functionality.
- Track identification.

## Judging Criteria

- Technical Depth & Engineering: 30%.
- Innovation & AI Creativity: 30%.
- Problem Value & Impact: 25%.
- Presentation & Documentation: 15%.

## DREAM Evidence Mapping

- Repository: `https://github.com/zemeng2015/dream-ai-engineering-copilot`
- License: `LICENSE`
- Track brief: `docs/qwencloud-submission.md`
- Qwen Cloud provider: `dream/llm/qwen_cloud.py`
- Qwen Cloud config: `examples/config/dream.qwen.yaml`
- Alibaba deployment proof file: `deploy/alibaba/serverless-devs.yaml`
- Architecture diagram: `docs/assets/qwencloud-architecture.png`
- Demo video handoff: `docs/qwencloud-video-upload-handoff.md`
- Demo video captions: `docs/qwencloud-demo-video-captions.srt`
- Alibaba proof screenshot target:
  `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`
- Alibaba proof recording target:
  `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`
- Final rules gate: `scripts/qwencloud-official-rules-gate.ps1`
- Final readiness gate: `scripts/qwencloud-final-readiness.ps1`
