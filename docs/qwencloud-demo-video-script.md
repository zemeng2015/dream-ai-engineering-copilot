<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Script

Target length: 2:30 (150 seconds).

Candidate: `artifacts/qwencloud-proof/video-v3/dream-v3-full-candidate.mp4`

## Direction

This is a founder-led product story, not an acceptance report. The arc is:

1. A stale-memory failure that could change a real rollout.
2. The Qwen/DREAM responsibility boundary in one sentence.
3. A continuous public run across three sessions.
4. The proof I personally needed before trusting persistence.
5. A transparent, limited benchmark and the deployed stack.
6. A quiet conclusion with time for the viewer to think.

The narration contains 243 words and 106.57 seconds of voice. The remaining
43.43 seconds are intentional visual breathing room, including 6.67 seconds of
silence on the closing frame.

## 0:00 - 0:16 A Concrete Failure

Narration:

> I changed a rollout from ten percent to twenty. The scary part? An agent can
> confidently bring back the old answer. In production, stale truth is worse
> than no memory.

Show the replaced 10% instruction, the current 20% instruction, and the agent
still choosing 10%. Do not introduce architecture yet.

## 0:16 - 0:27 The Boundary

Narration:

> So I built DREAM. Qwen understands what experience means; deterministic
> lifecycle rules decide what can come back.

Use only two roles: Qwen understands the update; DREAM makes stale truth
ineligible.

## 0:27 - 1:12 The Public Three-Session Run

Narration:

> This is the public build. It is running in Singapore, on Alibaba Function
> Compute.
>
> First, I set the canary at ten percent, for thirty minutes. Qwen recognizes
> the preference. It gives me an inspectable receipt.
>
> Then I change it to twenty percent for forty-five minutes. Qwen catches the
> conflict; DREAM keeps only the new value active.
>
> In a fresh session, DREAM returns twenty percent in nineteen of sixty-four
> tokens. The old instruction never enters context.

Each session begins with its real continuous browser clip and then settles on
a readable proof frame. Keep the runtime strip visible: `qwen3.7-plus`,
Tablestore, and build `cb6255b`.

## 1:12 - 1:40 The Proof I Needed

Narration:

> The test I cared about was persistence. I saved a Qwen-curated memory,
> rebuilt the same source, and forced a new Function Compute instance. The
> instance ID changed; the memory, decision, and Qwen receipt did not. Twenty
> simultaneous conflicting writes also succeeded, leaving one active truth and
> nineteen historical versions.

First show the two different FC instance IDs with the same memory, decision,
and provider request ID. Then show the archived public HTTP result:
`20/20 succeeded`, `1 active`, `19 historical`, and `0 errors / 429s`.

## 1:40 - 2:00 Transparent Measurement

Narration:

> In a clearly labeled synthetic evaluation, the same Qwen model improved from
> 25.3 to 48.7 across seven paired cases. A separate twenty-four-case lifecycle
> suite passed every recall, stale-leak, and token-budget check.

Keep `synthetic n=7`, `deterministic reference score`, and `Recall@12 35.6%`
visible. The benchmark supports the story; it is not presented as production
effectiveness.

## 2:00 - 2:17 Deployed Architecture

Narration:

> Underneath: Angular and FastAPI on Function Compute; Qwen Cloud for meaning;
> Tablestore transactions for one current truth; and temporary credentials from
> a narrow RAM role.

Use the deployed architecture diagram. Do not read IDs or implementation
details that are already visible.

## 2:17 - 2:30 Close

Narration:

> I do not want longer history. I want one current, reviewable truth, for the
> next decision.

Hold the public URL and three proof labels without narration for the final 6.67
seconds.

## Production Notes

- Narration: Alibaba Cloud Model Studio
  `qwen3-tts-instruct-flash-2026-01-26`, voice `Ethan`, instruction control on.
- Video: Remotion, 1920x1080 H.264, 30 fps, 150 seconds.
- Audio: 48 kHz stereo AAC, mastered to approximately -14 LUFS.
- Evidence validation: `tools/submission-video-v2/scripts/validate-v3.mjs`.
- Public video replacement remains blocked on Zack's approval of the local
  candidate.
