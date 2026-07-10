<!-- SPDX-License-Identifier: Apache-2.0 -->

# Leadership Product Readiness Audit

Audit date: 2026-07-10
Branch under review: `codex/leadership-pilot-candidate` (cumulative
provider-neutral Pilot chain based on the frozen leadership product)
Overall decision: **Synthetic leadership demo ready with warnings; real-source
Pilot remains No-Go.**

This audit uses current code, automated tests, generated preflight artifacts,
and named product documents as evidence. A missing external approval or live run
is recorded as incomplete rather than inferred from implementation intent.

## Requirement-by-Requirement Decision

| # | Requirement | Decision | Authoritative evidence | Remaining gap |
|---|---|---|---|---|
| 1 | Approved MemoryClaim affects Requirement/Jira and bounded PR Review; other statuses and unresolved conflicts stay out | **Proven for current scope** | Requirement same-case approval test; PR candidate/approved/rejected test; MemoryClaim policy tests; Context/Audit assertions | Core reviewer action roles exist; organization identity/role mapping and approval remain external |
| 2 | One consistent synthetic DFP scenario and evidence chain | **Proven for leadership path** | Fixed seed ids; double-reset acceptance; preflight source boundary; README examples now use `dfp-demo-repo` | Other legacy example directories remain in the repository but are outside the leadership path |
| 3 | Provider-neutral ten-minute leadership workflow | **Proven locally** | `/leadership-demo`; product profile tests; runbook; Angular build/tests; fixed seeded case; automated human-gate rehearsal | A timed rehearsal with the actual presenters and approved deployment is still required |
| 4 | Credible paired value evidence including citation, recall, unsupported claims, edit distance, latency, tokens, and cost | **Partially proven** | Same-provider/model/request/contract suite; alternating arm order; GPT-5.4 local synthetic suite; metric distributions; SME/pricing manifest gates | The live run is local and unapproved; no approved SME reference or exact provider pricing evidence yet |
| 5 | Deterministic reset/replay, smoke gate, fallback, stable runtime | **Proven locally** | `run_leadership_preflight.py`; reset/rehearsal tests; fallback/runbook; full Python and Angular verification; prior frozen leadership release | Exact custody-branch release freeze, approved deployment smoke and presenter-timed rehearsal remain pending |
| 6 | Enterprise trust boundary clear and first demo read-only/human-gated | **Core controls implemented; organization approval pending** | Signed proxy identity; role/source ACL enforcement and revocation; connector lifecycle; DLP; provider egress; runtime decision ledgers; v2 evidence export; Ed25519 custody; no-write scope | Approved SSO/proxy and connector deployment, shared/private storage, organization DLP/provider/network/residency/retention policy, managed keys and admin process remain pending |
| 7 | Executable one-team/one-app/one-repo Pilot proposal | **Proposal complete; organization decision pending** | Six-week proposal with scope, roles, baseline, metrics, gates, exit and leadership ask | Named sponsor/owners, application/repository, thresholds and Security/Data approval are unassigned |
| 8 | README/current-state/boundary/runbook match implementation and avoid inflated claims | **Proven for named current-state documents** | README; product-current-state; enterprise boundary; security/connector/DLP/provider/evidence/custody foundations; Human Rating and ROI disclaimers | Older research/handoff documents are historical context and must not be presented as current product truth |

## Verified Product Invariants

- `demo_team / dfp-demo-repo / examples/dfp-demo-repo` is the leadership contract.
- The fixed case is `case-leadership-async-status` and the fixed scan is
  `leadership-dfp-memory-v1`.
- The selected architecture claim is present in Requirement evidence, Context
  Trail, Context Pack, prompt sources, and reviewer proof.
- Exactly one material question remains open after reset, so Jira readiness is
  blocked until a human answers or explicitly waives it.
- The rehearsal answers that question, reaches Jira Ready with claim proof
  preserved, emits local Eval/Audit evidence, and restores the blocked baseline.
- Leadership/Workbench generation routes through the backend `config` selector;
  the checked-in public configuration still defaults to `mock` with no LLM
  judge. GPT-5.4 requires an explicit local/private environment override.
  Qwen/Qwen-judge behavior remains restricted to the Hackathon profile.
- PR Review returns the selected claim ids, conflict-blocked ids, and a working
  PR Context Trail/Pack/Prompt API path.
- Benchmark fixture runs are labeled `harness_validation` and cannot satisfy the
  live-model evidence gate.
- Human edit distance requires an approved, hash-verified SME manifest.
- Cost requires an approved exact-provider/model pricing manifest plus separate
  input and output token counts.
- Private runtime identity and DefaultAccessPolicy decisions are persisted as
  metadata-only evidence; unsigned team assertions are never trusted for tenant
  attribution.
- Evidence bundle v2 exports eleven fixed sections, remains compatible with v1,
  and can receive a detached Ed25519 receipt without changing bundle contents.
- A valid custody receipt proves possession of the matching private key and
  byte/root binding only when the public key is independently trusted. It does
  not prove organization approval or legal non-repudiation.

## Current Verification Baseline

```text
Python: 309 passed, 1 skipped
Ruff: passed
Angular production build: passed
Angular ChromeHeadless tests: 23 passed
Angular production/full dependency audit: 0 vulnerabilities
Leadership preflight: ready_for_demo=true
Raw-document acceptance: passed
Strict preflight: passed on the committed custody predecessor; final candidate rerun pending
Candidate presentation release freeze: pending final integration commit
```

The current test count is evidence for the audited working tree only. Rerun all
commands on the frozen presentation commit; do not quote this count after code
changes without a fresh run.

## Local GPT-5.4 Synthetic Evidence

On 2026-07-10, the paired runner completed three repetitions (six calls) using
the OpenAI endpoint, requested model `gpt-5.4`, and resolved model
`gpt-5.4-2026-03-05`. Both arms used the same provider, model, request, output
contract, and alternating arm order; only the DREAM source catalog differed.

The real Requirement/Jira product path was also smoke-tested with the frontend's
`config` selector and an explicit local `DREAM_LLM_PROVIDER=openai-compatible`
override. It resolved to `gpt-5.4-2026-03-05`, used 31 source paths, preserved
the approved MemoryClaim in the generated draft, and kept the Human Gate closed
with one open question. The checked-in configuration remains `mock`.

After separating retrieval coverage from model-output coverage and fixing the
file/symbol dedupe ranking, the current local report recorded:

- DREAM source-catalog recall: 100% for code, tests, and history;
- DREAM valid citations: mean 54.0 per run, 100% validity;
- impact recall: 0% stateless versus 86.7% DREAM;
- test recall: 0% stateless versus 100% DREAM;
- history recall: 0% stateless versus 93.3% DREAM;
- critical-question recall: 0% stateless versus 33.3% DREAM;
- unsupported claims: mean 5.67 stateless versus 5.0 DREAM;
- total tokens: mean 773 stateless versus 5,420 DREAM;
- latency: mean 2.61 seconds stateless versus 11.36 seconds DREAM.

Critical-question coverage remains the clearest output-quality gap. The scorer
now compares each question independently with normalized domain terms, but the
golden set and thresholds still require SME approval. This run uses only
synthetic DFP data and is local technical evidence, not enterprise approval or
a production ROI claim. Human edit distance and cost remain unmeasured until
approved SME and pricing manifests exist.

## Leadership Claim Boundary

Safe claim today:

> DREAM demonstrates, on a synthetic Forecast Platform scenario, that governed
> approved engineering memory can be selected, placed into the actual generation
> context, traced to source/reviewer proof, evaluated, and held behind a human
> decision gate.

Claims that are not yet supported:

- DREAM improves production engineering productivity or ROI.
- DREAM is approved for real organization data.
- A production connector automatically synchronizes source-system ACLs and
  identity lifecycle.
- DREAM's local JSON/SQLite evidence stores satisfy enterprise retention,
  availability, legal hold or SIEM requirements.
- A locally valid Ed25519 receipt proves the organization approved the signer,
  key, data, model or Pilot result.
- Human Ratings improve future retrieval or model behavior.
- The provider/model cost or quality is known for the proposed Pilot.
- DREAM can safely write Jira tickets or PR actions.

## Required Evidence Before the Leadership Meeting

1. Review and commit the product changes; run preflight with `--strict-git`.
2. Build and smoke the exact approved deployment or documented local fallback.
3. Conduct one timed ten-minute rehearsal using the fixed reset.
4. Decide whether the meeting presents only synthetic technical proof or also an
   approved live-model suite. Do not improvise a provider switch during the demo.
5. Keep the Pilot ask, owners-to-assign, and No-Go real-source boundary visible.
6. If custody is demonstrated, verify against an independently retained public
   key and explicitly label it a local cryptographic foundation.

## Required Evidence Before Real-Source Pilot Approval

1. Named sponsor, Pilot owner, technical owner, Security/Data owner, source owner,
   and SME reviewers.
2. Approved private deployment/data flow and threat model.
3. Organization-approved SSO/proxy deployment and production connector ACL/
   identity synchronization; rerun the existing negative access tests there.
4. Approved read-only connector, DLP taxonomy/operations, private shared storage,
   deletion/retention, region and network/provider controls.
5. Frozen SME baseline and thresholds created before viewing Pilot results.
6. Approved provider/model suite with exact provider/model/token/pricing evidence.
7. Demonstrated disable, incident response, signed audit export, custody and
   deletion procedure using organization-approved keys and storage.

Until these conditions are met, DREAM can support a leadership demonstration and
Pilot-design discussion, but it must not ingest real organization sources.
