# SPDX-License-Identifier: Apache-2.0

# Qwen Cloud Demo Video Script

Target length: about 2:04.

## 0:00 - 0:15 The Memory Problem

Open `/hackathon-demo`.

Narration:

"Most AI assistants start every session from zero. DREAM gives Qwen durable
experience, then governs conflicts, forgetting, context budgets, provenance,
and feedback. This is not another chat screen. It is a memory lifecycle."

Keep the Track 1 label, Qwen model signal, Alibaba runtime signal, and the live
three-session command visible.

## 0:15 - 0:37 Live Three-Session Arena

Click `Run Live 3-Session Proof` and keep the three session cards visible as
they complete.

Narration:

"In Session 1, Qwen recognizes a durable rollout preference and returns
remember. In Session 2, the user changes the same preference. Qwen returns
supersede, and DREAM marks the old value inactive instead of keeping two
conflicting truths. Session 3 starts with no prompt history. Under a 64-token
budget, DREAM recalls only the current 20 percent canary for 45 minutes. The old
10 percent value does not leak."

Call out the visible proof:

- Qwen actions: `remember`, then `supersede`
- Old status: `superseded`
- Active count: `1`
- Recall budget: `19 / 64` in the recorded run
- Selected memories: `1`
- Old value leaked: `no`

Click `Mark Helpful + Correct` and show `Feedback Recorded`.

The published video uses the continuous live capture with visible Qwen Cloud
receipts; it does not splice the three lifecycle requests into separate takes.

## 0:37 - 1:05 Measured Impact and Lifecycle Safety

Scroll to the benchmark band.

Narration:

"The same model is evaluated with and without DREAM memory. Qwen plus DREAM
scores 48.7 versus 25.3, wins all seven paired cases, and improves the
deterministic reference score by 23.4 points. The same lifecycle is tested
beyond one polished demo. We ran 37 real Qwen
curator decisions across 24 synthetic cases covering cross-session preference,
conflict supersession, TTL, explicit forgetting, duplicate rejection, and
limited context. All 24 lifecycle cases passed, critical recall was 100 percent,
forbidden leak was zero, and token-budget compliance was 100 percent."

Briefly show `docs/qwen-experience-memory-benchmark.md` or the machine-readable
summary if time allows.

## 1:05 - 1:33 Source Governance to Engineering Output

Open Memory Hub, then Requirement Flow.

Narration:

"Experience is only one memory layer. Organizational claims must retain source
proof and human approval. Unresolved conflicts are blocked from retrieval. The
approved current truth then enters the same Requirement Case prompt, impact
map, engineering brief, and Jira draft with reviewer and source provenance."

Show one approved claim, one blocked conflict warning, and the resulting Jira
context or context trail.

## 1:33 - 2:04 Alibaba Proof and Close

Return to the Arena or open `/health` beside `/qwencloud/showcase`.

Narration:

"DREAM runs on Alibaba Cloud Function Compute with qwen3.7-plus. The live
runtime, public benchmark, full report, tests, and deployment template are all
in the repository. DREAM helps Qwen remember the right experience, replace old
truth, forget safely, and explain what it used."

End on the Arena lifecycle ledger and the `24/24` benchmark result.
