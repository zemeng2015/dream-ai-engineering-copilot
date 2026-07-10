<!-- SPDX-License-Identifier: Apache-2.0 -->

# Current Development Handoff

Status date: 2026-07-10

This is the authoritative short engineering handoff for the cumulative
provider-neutral leadership/Pilot candidate. Older planning and UI handoffs are
historical context, not current branch or capability truth.

## Product and Branch Boundary

DREAM is a governed Engineering Memory and Decision Workbench. The fixed
leadership story turns an ambiguous synthetic Forecast Platform request into a
source-backed impact map, role questions, human-gated Jira draft, Context Trail,
Eval and Audit evidence. It does not autonomously write to Jira, GitHub,
deployment, email or messaging systems.

The integration branch is:

```text
codex/leadership-pilot-candidate
```

Its history is a linear accumulation of the frozen leadership product followed
by Pilot security, Angular dependency remediation, connector lifecycle, DLP,
provider egress, evidence export, runtime security decisions and Ed25519 evidence
custody. No merge or cherry-pick from the Qwen competition worktree is required.

The Qwen/Hackathon worktree and routes remain separate competition assets. Do
not use them as a leadership fallback or merge competition-only UI, provider,
benchmark, deployment configuration or submission material into this candidate.

## Fixed Leadership Contract

```text
team_id   = demo_team
repo_name = dfp-demo-repo
repo_path = examples/dfp-demo-repo
case_id   = case-leadership-async-status
scan_id   = leadership-dfp-memory-v1
route     = /leadership-demo
```

The checked-in provider remains `mock`. A GPT-5.4/OpenAI-compatible run requires
an explicit private/local configuration and exact provider approval; do not
switch providers during a presentation.

## Implemented Pilot Foundations

- approved MemoryClaims enter Requirement/Jira and bounded PR Review prompts;
- unresolved conflicts and unapproved claims stay out;
- signed proxy identity, action roles, source ACL filtering and revocation;
- derived artifact ACL lineage and connector revoke-first cleanup;
- Angular 21 production dependency baseline with zero current npm findings;
- deterministic pre-index/pre-prompt/pre-persist/post-response DLP;
- exact time-bounded private provider endpoint/model approval and egress evidence;
- metadata-only identity and DefaultAccessPolicy decision ledgers;
- team-scoped Pilot evidence bundle v2 with v1 verification compatibility; and
- detached Ed25519 custody receipts verified against an independently trusted
  public key.

These are public-core engineering controls. They are not organization approval
for real company data.

## Local Runtime

Backend:

```powershell
uvicorn dream.api.app:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm start --prefix frontend -- --host 127.0.0.1 --port 4200
```

Reset the deterministic leadership scenario before rehearsal:

```powershell
python scripts/seed_leadership_demo.py --reset
```

## Candidate Verification and Freeze

Run from this worktree on the exact commit being presented:

```powershell
python -m ruff check .
python -m pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend audit --omit=dev
npm --prefix frontend audit
python scripts/verify_raw_doc_memory_flow.py
python scripts/run_leadership_preflight.py --strict-git --require-frontend-bundle
python scripts/run_leadership_rehearsal.py
python scripts/build_leadership_release.py --strict
python scripts/verify_leadership_release.py
```

The release manifest binds the entire Git-visible source snapshot and explicitly
checksums leadership plus Pilot security/evidence/custody critical files. A
`frozen` manifest proves a clean reproducible local presentation snapshot, not
enterprise production readiness.

## Evidence Bundle and Custody

Offline evidence administration remains outside the private API:

```powershell
dream audit export-bundle --team <team> --confirm-team <team> `
  --operator <operator> --reason <reason>

dream audit sign-bundle --bundle <bundle-dir> `
  --expected-root-sha256 <reviewed-export-root> `
  --private-key <approved-ed25519-private-pem> `
  --key-id <approved-key-id> --signer <operator> --reason <reason>

dream audit verify-signature --bundle <bundle-dir> `
  --receipt <detached-receipt> --public-key <independent-trust-key> `
  --expected-key-id <approved-key-id>
```

Signing/private trust keys must remain outside both checkout and artifact roots.

## Real-Source No-Go Boundary

Do not ingest organization sources until named owners approve the exact Pilot
data flow. Still external or incomplete:

- organization SSO/proxy deployment and identity/group lifecycle;
- approved production read-only connector and source ACL synchronization;
- shared private transactional storage, backup, retention/deletion and legal hold;
- approved DLP taxonomy/operations, network, region and provider terms;
- managed signing keys, rotation/revocation, immutable custody and SIEM/GRC;
- approved SME golden baseline, thresholds and exact provider pricing; and
- timed presenter rehearsal plus approved deployment smoke.

## Handoff Decision

This candidate has passed its strict local integration release gate and is
suitable for final local product acceptance and a synthetic leadership
demonstration. Rebuild the manifest after any later commit. It remains No-Go
for real-source Pilot activation until the external gates above are assigned and
approved. Keep the long-term goal active; do not mark enterprise Pilot readiness
complete based only on local tests or cryptographic receipts.
