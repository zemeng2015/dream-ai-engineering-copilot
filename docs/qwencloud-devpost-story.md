## Inspiration

The dangerous memory failure is not forgetting everything. It is remembering yesterday's instruction as if it were still true. A rollout changes from 10% to 20%, but an agent quietly retrieves both values. The answer still sounds confident, and the stale guidance is hard to see.

We built DREAM so Qwen can carry useful experience across sessions without turning memory into an ungoverned pile of text.

## What it does

DREAM gives Qwen governed cross-session experience. Qwen reads a natural-language observation and decides whether it should be remembered, supersede an older truth, be forgotten, or be ignored. DREAM then applies deterministic lifecycle rules for conflict replacement, TTL expiration, explicit forgetting, provenance, feedback ranking, and recall under a hard context budget.

The public Judge Arena demonstrates one continuous flow across three separate sessions. Session 1 remembers a durable rollout preference. Session 2 changes that preference and supersedes the stale value. Session 3 recalls only the current 20% canary in 19 of 64 available tokens, without leaking the old 10% value. Each semantic decision exposes a real Qwen provider receipt instead of a mocked response.

## How we built it

- `qwen3.7-plus` performs semantic memory curation through the Qwen Cloud OpenAI-compatible API.
- FastAPI exposes the memory lifecycle, proof, and engineering workflow APIs.
- DREAM enforces one current truth, bounded recall, forgetting, provenance, and reviewable history after Qwen proposes the semantic action.
- Alibaba Tablestore stores durable governed experience. Partition-local transactions atomically replace the active value while retaining superseded history.
- Alibaba Cloud Function Compute runs the public Singapore deployment with a narrow RAM execution role and temporary table-scoped credentials.
- Angular provides the Judge Arena, live receipts, lifecycle state, and evidence views.

This responsibility boundary is deliberate: Qwen understands meaning; DREAM and Tablestore enforce state invariants.

## Proof, not just a claim

We built the submission around evidence that a judge can inspect:

- **Live Qwen flow:** remember, supersede, and constrained recall run against the public deployment with real provider request IDs.
- **Cross-instance durability:** DREAM saved one Qwen-curated memory, rebuilt and redeployed the same source, then verified from a different Function Compute instance that the same memory ID, decision ID, and Qwen provider request ID remained in Tablestore.
- **Contention:** 20 simultaneous public conflicting writes completed 20/20 with no errors or 429s. Tablestore committed one active truth and retained 19 historical versions.
- **Lifecycle benchmark:** 37 real Qwen curator decisions ran across 24 synthetic cases. All 24/24 passed; critical-memory recall was 100%, forbidden-memory leak was 0%, and token-budget compliance was 100%.
- **Paired grounding comparison:** with the same `qwen3.7-plus` model, temperature, and output contract, the deterministic reference score increased from 25.3 to 48.7 with DREAM evidence, a +23.4 change with 7/7 paired wins.

The benchmarks are small, reproducible synthetic evaluations, not production-effectiveness claims. Exact retrieval Recall@12 in the paired comparison remains 35.6%, and we do not claim latency or token improvements because those sidecars are incomplete.

## Challenges

The hardest part was separating semantic judgment from deterministic safety. Qwen must understand whether a statement is durable, conflicting, temporary, reusable, or noise. The storage layer must still guarantee that stale, expired, forgotten, and budget-excluded values cannot quietly re-enter context.

The second challenge was proving cloud durability rather than merely showing a successful request. That required preserving Qwen receipts, redeploying onto a different Function Compute instance, exercising conflicting public writes, and publishing sanitized evidence without exposing credentials.

## Accomplishments

We shipped a real Qwen MemoryAgent with visible lifecycle decisions, one-current-truth semantics, timely forgetting, constrained recall, feedback, and source provenance. The same competition branch is reproducible through CI, deploy proof, benchmark runners, video validation, and a hash-locked submission bundle.

## Significant hackathon-period updates

DREAM began during the submission period as a provider-neutral, source-backed engineering memory framework. For this hackathon we added the Qwen Cloud curator, governed cross-session experience, conflict supersession, TTL and explicit forgetting, feedback-aware constrained recall, provider receipts, the live Judge Arena, Tablestore persistence, Function Compute deployment, contention and cross-instance proofs, and the V3 submission experience.

## What's next

Next we would expand the benchmark with human-reviewed production scenarios, add encrypted multi-tenant isolation, and upstream only provider-neutral lifecycle primitives into the broader DREAM framework.
