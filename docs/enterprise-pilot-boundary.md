<!-- SPDX-License-Identifier: Apache-2.0 -->

# Enterprise Pilot Boundary

This document defines the minimum trust boundary for a controlled DREAM Pilot.
It is a target operating contract, not a claim that the public repository
already supplies every enterprise control.

## Pilot Shape

- one sponsor team;
- one application;
- one repository;
- a small, explicitly approved source set;
- read-only ingestion and retrieval;
- human approval before any artifact is used for delivery; and
- no automatic Jira, GitHub, deployment, messaging, or email writes.

## Data Flow

```text
Approved read-only sources
  -> connector identity + source ACL metadata
  -> private ingestion boundary
  -> classification / redaction / provenance
  -> private indexes, evidence graph, and memory ledger
  -> ACL-aware retrieval
  -> approved enterprise model endpoint
  -> human-reviewed draft
  -> audit record and evaluation
```

The public synthetic DFP pack must remain separate from private organization
content. Private connector configuration, credentials, source snapshots, model
configuration, and deployment state belong in a private extension/deployment
repository.

## Required Controls Before Real Sources

| Control | Pilot requirement | Current public-core status |
|---|---|---|
| Identity | Organization-approved SSO and named user identity | Signed-proxy identity contract implemented; organization SSO/proxy approval pending |
| Authorization | Role policy for source onboarding, memory review, retrieval, and audit | Core action roles and fail-closed private routes implemented; administration surfaces remain blocked |
| ACL propagation | Preserve source ACLs and filter every retrieval result for the caller | Core source-to-prompt propagation, derived lineage, retrieval filtering, revocation, and registered artifact cleanup implemented; production connector/shared store pending |
| Connectors | Read-only, least-privilege, allowlisted repository/path scope | Provider-neutral lifecycle contract and synthetic/local adapters only; approved production connector pending |
| Data classification | Approved categories, blocked content, source labels | `ResourceAccess` classification/ACL lineage implemented; enterprise taxonomy/policy pending |
| Redaction/DLP | Pre-index, pre-prompt, selected pre-persist, and post-response enforcement with adversarial corpus | Versioned deterministic foundation implemented; enterprise taxonomy, binary/OCR scanning, exceptions and approved production policy pending |
| Provider boundary | Approved endpoint, region, retention, and no-training terms | Provider abstraction exists; approval external |
| Network | Private egress policy and endpoint allowlist | Deployment-specific, not provided |
| Secrets | Enterprise secret manager, rotation, no client exposure | Environment variables in local core |
| Storage | Encrypted private storage, backup, retention, deletion | Local JSON/SQLite artifacts |
| Audit | Named actor, source use, provider/model, decision and export | Local structured audit; export/admin controls pending |
| Incident response | Owner, disable switch, investigation and deletion procedure | Pilot process required |
| Dependency security | Approved supported runtime and remediated/excepted dependency findings | Angular 21 repository baseline passes production/full npm audits; organization runtime approval pending |

Any missing control above is a go-live blocker for real organization data unless
the security owner records an explicit, time-bounded exception.

## Retrieval and Memory Policy

- Candidate, rejected, and quarantined semantic claims cannot enter generation.
- Approved claims in unresolved conflicts are blocked.
- Auto-approved deterministic code facts and human-approved semantic claims must
  remain distinguishable.
- Source deletion or access revocation must invalidate derived chunks, claims,
  indexes, prompt caches, and future retrieval.
- Every selected claim must retain source path/span/hash where available,
  reviewer identity/time, policy status, and downstream run references.
- A user must never gain access to a source through DREAM that they could not
  access in the source system.

The current public core supplies tested ACL-aware retrieval, source lifecycle,
revocation, and registered artifact cleanup foundations. It does not supply a
production connector, organization-approved identity deployment, shared
transactional lifecycle store, or approved deletion SLA. See
[Pilot Security Foundation](pilot-security-foundation.md) and
[Connector Source Lifecycle Foundation](connector-lifecycle-foundation.md).
The [DLP Enforcement Foundation](dlp-enforcement-foundation.md) records
metadata-only decisions and prevents known redaction/block classes from entering
derived indexes and model calls, but it is not approval to ingest company data.

## Human Gate and Side Effects

During the Pilot, DREAM may create a draft inside its own private workspace. It
must not create or modify Jira tickets, PR comments, approvals, merges, branches,
deployments, or production configuration. Export or copy/paste is a deliberate
human action outside the system.

Any future write integration requires a separate approval scope, preview,
explicit confirmation, idempotency key, target allowlist, rollback procedure,
and audit event.

## Logging and Evaluation

Allowed operational logs must exclude source bodies, prompts, model responses,
credentials, customer data, and sensitive payloads unless an approved logging
policy explicitly permits a redacted field. Metrics should use identifiers and
aggregates wherever possible.

Pilot evaluations must separate:

- synthetic benchmark evidence;
- SME-reviewed Pilot evidence;
- operational reliability evidence; and
- any later productivity/ROI claim.

No synthetic benchmark is a substitute for the Pilot baseline.

## Go/No-Go Gates

Real-source ingestion remains **No-Go** until Security, Data/Privacy, the source
owner, and the Pilot technical owner approve the data flow and control matrix.

The Pilot pauses immediately on:

- an ACL bypass or unauthorized source citation;
- sensitive-data leakage to logs, artifacts, or an unapproved provider;
- an external write attempt;
- unverifiable source provenance for a high-impact recommendation;
- repeated hallucinated organization references above the agreed threshold; or
- inability to delete Pilot data within the agreed window.

## Exit and Deletion

At Pilot end, the owner must export the agreed metrics, revoke credentials,
disable connectors, delete private source copies and derived artifacts according
to retention policy, and record whether the Pilot advances, extends under new
approval, or stops.
