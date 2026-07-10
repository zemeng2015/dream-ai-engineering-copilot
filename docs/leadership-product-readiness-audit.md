<!-- SPDX-License-Identifier: Apache-2.0 -->

# Leadership Product Readiness Audit

Audit date: 2026-07-10
Branch under review: `codex/leadership-product`
Overall decision: **Synthetic leadership demo ready with warnings; real-source
Pilot remains No-Go.**

This audit uses current code, automated tests, generated preflight artifacts,
and named product documents as evidence. A missing external approval or live run
is recorded as incomplete rather than inferred from implementation intent.

## Requirement-by-Requirement Decision

| # | Requirement | Decision | Authoritative evidence | Remaining gap |
|---|---|---|---|---|
| 1 | Approved MemoryClaim affects Requirement/Jira and bounded PR Review; other statuses and unresolved conflicts stay out | **Proven for current scope** | Requirement same-case approval test; PR candidate/approved/rejected test; MemoryClaim policy tests; Context/Audit assertions | Enterprise reviewer authorization is not implemented |
| 2 | One consistent synthetic DFP scenario and evidence chain | **Proven for leadership path** | Fixed seed ids; double-reset acceptance; preflight source boundary; README examples now use `dfp-demo-repo` | Other legacy example directories remain in the repository but are outside the leadership path |
| 3 | Provider-neutral ten-minute leadership workflow | **Proven locally** | `/leadership-demo`; product profile tests; runbook; Angular build/tests; fixed seeded case; automated human-gate rehearsal | A timed rehearsal with the actual presenters and approved deployment is still required |
| 4 | Credible paired value evidence including citation, recall, unsupported claims, edit distance, latency, tokens, and cost | **Partially proven** | Same-provider/model/request/contract suite; alternating arm order; metric distributions; SME/pricing manifest gates | No approved live provider run, approved SME reference, or real provider pricing evidence yet |
| 5 | Deterministic reset/replay, smoke gate, fallback, stable runtime | **Proven locally; release not frozen** | `run_leadership_preflight.py`; reset/rehearsal tests; fallback/runbook; full Python and Angular verification; verified checksummed candidate manifest | Working tree is uncommitted; strict-git frozen manifest and approved deployment smoke have not passed |
| 6 | Enterprise trust boundary clear and first demo read-only/human-gated | **Boundary documented; enterprise controls absent** | Enterprise Pilot boundary; no-write Pilot scope; product profile uses mock/none by default | SSO, ACL propagation, private connectors, DLP/redaction, private storage, residency and admin controls are not implemented |
| 7 | Executable one-team/one-app/one-repo Pilot proposal | **Proposal complete; organization decision pending** | Six-week proposal with scope, roles, baseline, metrics, gates, exit and leadership ask | Named sponsor/owners, application/repository, thresholds and Security/Data approval are unassigned |
| 8 | README/current-state/boundary/runbook match implementation and avoid inflated claims | **Proven for named documents** | README roadmap/example cleanup; product-current-state limitations; Human Rating and ROI disclaimers; preflight docs check | Older research/handoff documents are historical context and must not be presented as current product truth |

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
- Leadership/Workbench generation defaults to `mock` with no LLM judge;
  Qwen/Qwen-judge behavior is restricted to the explicit Hackathon profile.
- PR Review returns the selected claim ids, conflict-blocked ids, and a working
  PR Context Trail/Pack/Prompt API path.
- Benchmark fixture runs are labeled `harness_validation` and cannot satisfy the
  live-model evidence gate.
- Human edit distance requires an approved, hash-verified SME manifest.
- Cost requires an approved exact-provider/model pricing manifest plus separate
  input and output token counts.

## Current Verification Baseline

```text
Python: 205 passed, 1 skipped
Angular production build: passed
Angular ChromeHeadless tests: 23 passed
Leadership preflight: ready_for_demo=true
Preflight warning: working tree has uncommitted changes
```

The current test count is evidence for the audited working tree only. Rerun all
commands on the frozen presentation commit; do not quote this count after code
changes without a fresh run.

## Leadership Claim Boundary

Safe claim today:

> DREAM demonstrates, on a synthetic Forecast Platform scenario, that governed
> approved engineering memory can be selected, placed into the actual generation
> context, traced to source/reviewer proof, evaluated, and held behind a human
> decision gate.

Claims that are not yet supported:

- DREAM improves production engineering productivity or ROI.
- DREAM is approved for real organization data.
- DREAM preserves source-system ACLs.
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

## Required Evidence Before Real-Source Pilot Approval

1. Named sponsor, Pilot owner, technical owner, Security/Data owner, source owner,
   and SME reviewers.
2. Approved private deployment/data flow and threat model.
3. SSO and caller-aware source ACL enforcement with negative access tests.
4. Approved read-only connectors, redaction/DLP, storage, deletion/retention,
   region and network/provider controls.
5. Frozen SME baseline and thresholds created before viewing Pilot results.
6. Approved provider/model suite with exact provider/model/token/pricing evidence.
7. Demonstrated disable, incident response, audit export, and deletion procedure.

Until these conditions are met, DREAM can support a leadership demonstration and
Pilot-design discussion, but it must not ingest real organization sources.
