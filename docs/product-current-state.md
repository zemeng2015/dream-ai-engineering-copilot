<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Product Current State

Status date: 2026-07-10

## Product Definition

DREAM is a governed Engineering Memory and Decision Workbench. It converts
approved organizational documents, code, historical engineering events, and
human decisions into source-backed context for reviewable engineering work.
It is not a general chatbot and it does not autonomously approve or execute
delivery actions.

The current leadership scenario turns a rough Forecast Platform request into an
impact map, role-specific questions, a human-gated Jira draft, source proof, and
an Eval/Audit trail using synthetic DemoCorp/DFP data.

## Implemented and Verified

| Capability | Current implementation | Verification |
|---|---|---|
| Source intake | Register/upload, parse, metadata edit, review, promote, source hash/span proof | Intake/API tests |
| Governed memory | Deterministic scans, candidates, review ledger, approve/reject/quarantine, conflict reporting | Memory distillation tests |
| Requirement Case | Rough request, retrieved evidence, impact, questions, brief, Jira draft, readiness | Requirement Case tests |
| Approved claim use | Policy-approved claims enter Requirement/Jira prompts; other statuses do not | Same-case approval tests |
| PR Review reuse | Policy-approved claims enter PR prompt, response sources, Context Trail/Pack, and Audit | PR Review policy test |
| Conflict policy | Approved claims in unresolved single-value conflicts are blocked with warnings | Retriever/policy tests |
| Trust proof | Sources, claim provenance, reviewer identity/time, Context Trail, prompt preview, Audit and Eval | Context and leadership tests |
| Leadership replay | Fixed `demo_team / dfp-demo-repo` scenario with reset, stable case/scan ids, one open human gate | Leadership seed acceptance test |
| Human-gate rehearsal | Blocked -> named answer -> Jira Ready -> proof retained -> blocked baseline restored | Rehearsal runner/test/report |
| Paired A/B harness | Same provider/model/request/contract; only context changes; honest missing metrics | Benchmark invariant tests |
| Cost evidence gate | Exact provider/model pricing manifest plus input/output token proof | Pricing manifest tests |
| External writes | None in the leadership scenario | Product boundary and implementation |
| Pilot security foundation | Signed proxy identity, source ACL model/propagation, fail-closed private routes, derived artifact ACL | Security policy, API, retrieval and no-leak tests |
| Frontend dependency baseline | Angular 21, TypeScript 5.9, `@angular/build`, zero production/full npm audit | Lockfile, build, ChromeHeadless and CI gates |
| Connector source lifecycle | Metadata-only sync/tombstone contract, immutable ACL versions, revoke-first cleanup, registered artifact cascade | Connector lifecycle, restart, path-safety and cleanup-failure tests |

The verified local suite currently covers Python services, the Angular build,
and ChromeHeadless component tests. See the leadership runbook for the latest
commands; do not copy a historical pass count into a leadership claim without
rerunning the suite on the presentation commit.

## Current Product Loop

```text
Synthetic approved sources + DFP code
  -> intake / index / graph / MemoryClaim scan
  -> human memory review and conflict policy
  -> Requirement Case or PR Review retrieval
  -> approved claims + source evidence enter the actual prompt
  -> human-gated engineering output
  -> sources_used + Context Trail + prompt preview
  -> deterministic Eval + Audit + optional human rating
```

The generation loop is closed for Requirement Case/Jira and the bounded PR
Review workflow. Human ratings are persisted, but they do not yet alter ranking,
policy, or future generations.

## Demonstration-Ready Boundary

The current system is suitable for a controlled leadership demonstration when:

- the deterministic seed/reset and smoke checks pass;
- only synthetic DFP data is loaded;
- the provider is local/mock or explicitly approved;
- no Jira, GitHub, email, or other external write path is enabled;
- one material question remains open to demonstrate the human gate; and
- all benchmark results are labeled with their evidence tier and limitations.

## Not Yet Enterprise-Ready

The public core does not currently prove:

- organization-approved SSO/proxy deployment and complete role-based administration;
- approved production connectors, shared lifecycle storage, and deletion SLA;
- approved production GitHub/Jira/document connectors;
- enterprise redaction/DLP policy and classification enforcement;
- production secrets management, storage hardening, backup, or retention;
- organization-approved data residency and network egress controls;
- production-scale availability, latency, cost, or support SLOs;
- organization approval of the remediated frontend dependency/runtime baseline;
- a feedback-learning policy driven by Human Rating;
- production ROI; or
- safe automatic Jira/PR creation, comments, approval, merge, or deployment.

These are Pilot gates, not implied current capabilities.

## Evidence Status

- The DFP dataset and golden profiles are synthetic.
- The fixture A/B report validates the harness only.
- A live provider-neutral model report still requires an approved endpoint and
  must be presented as early technical evidence, not ROI.
- Retrieval recall has known misses; zero or low metric values must remain in
  reports rather than being hidden.
- The Qwen competition branch and benchmark are separate assets and are not the
  Fannie-facing product evidence baseline.

## Immediate Product Priorities

1. Run and review the implemented three-repetition suite on an approved endpoint.
2. Have BA/TL/QA SMEs approve the first hash-verified reference manifest and
   impact set using the public draft template only as a starting structure.
3. Complete the Pilot security/data-flow review before connecting any company
   source.
4. Preserve small, reviewable product commits and keep competition-only code out
   of this branch.

The provider-neutral public core now contains the first Pilot security slices.
See `docs/pilot-security-foundation.md` and
`docs/connector-lifecycle-foundation.md`. These implementations reduce technical
risk but do not change the real-source No-Go decision.
