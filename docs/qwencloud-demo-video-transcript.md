<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Demo Video Transcript

This transcript matches `docs/qwencloud-demo-video-captions.srt`.

## Transcript

Most AI assistants start every session from zero. DREAM gives Qwen Cloud durable
experience, then governs conflicts, forgetting, context budgets, provenance,
and feedback.

In Session 1, Qwen recognizes a durable rollout preference and returns
remember. In Session 2, the user changes the same preference. Qwen returns
supersede, and DREAM marks the old value inactive instead of keeping two
conflicting truths.

Session 3 starts with no prompt history. Under a 64-token budget, DREAM recalls
only the current 20 percent canary for 45 minutes. The old 10 percent value does
not leak. Helpful and correct feedback is written back to future ranking.

The same lifecycle is tested beyond one polished demo. We ran 37 real Qwen
curator decisions across 24 synthetic cases covering cross-session preference,
conflict supersession, TTL, explicit forgetting, duplicate rejection, and
limited context.

All 24 lifecycle cases passed. Critical recall was 100 percent, forbidden leak
was zero, and token-budget compliance was 100 percent.

Experience is only one memory layer. Organizational claims must retain source
proof and human approval. Unresolved conflicts are blocked from retrieval.

The approved current truth enters the same Requirement Case prompt, impact map,
engineering brief, and Jira draft with reviewer and source provenance.

DREAM runs on Alibaba Cloud Function Compute with qwen3.7-plus. The live
runtime, public benchmark, full report, tests, and deployment template are in
the repository.

DREAM helps Qwen remember the right experience, replace old truth, forget
safely, and explain what it used.
