<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Transcript

This transcript matches `docs/qwencloud-demo-video-captions.srt` and the V3
candidate rendered from `tools/submission-video-v2/src/v3/narration.json`.

## Transcript

I changed a rollout from ten percent to twenty. The scary part? An agent can
confidently bring back the old answer. In production, stale truth is worse than
no memory.

So I built DREAM. Qwen understands what experience means; deterministic
lifecycle rules decide what can come back.

This is the public build. It is running in Singapore, on Alibaba Function
Compute.

First, I set the canary at ten percent, for thirty minutes. Qwen recognizes the
preference. It gives me an inspectable receipt.

Then I change it to twenty percent for forty-five minutes. Qwen catches the
conflict; DREAM keeps only the new value active.

In a fresh session, DREAM returns twenty percent in nineteen of sixty-four
tokens. The old instruction never enters context.

The test I cared about was persistence. I saved a Qwen-curated memory, rebuilt
the same source, and forced a new Function Compute instance. The instance ID
changed; the memory, decision, and Qwen receipt did not. Twenty simultaneous
conflicting writes also succeeded, leaving one active truth and nineteen
historical versions.

In a clearly labeled synthetic evaluation, the same Qwen model improved from
25.3 to 48.7 across seven paired cases. A separate twenty-four-case lifecycle
suite passed every recall, stale-leak, and token-budget check.

Underneath: Angular and FastAPI on Function Compute; Qwen Cloud for meaning;
Tablestore transactions for one current truth; and temporary credentials from
a narrow RAM role.

I do not want longer history. I want one current, reviewable truth, for the next
decision.
