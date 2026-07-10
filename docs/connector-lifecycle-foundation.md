<!-- SPDX-License-Identifier: Apache-2.0 -->

# Connector Source Lifecycle Foundation

Status date: 2026-07-10

## Decision

DREAM now has a provider-neutral, metadata-only connector lifecycle contract for
private Pilot extensions. It does not implement a production GitHub, Jira, or
document connector. It defines and tests what every approved connector must do
when a source appears, changes, loses access, or is deleted.

The safety order is deliberate:

```text
signed source-admin identity
  -> validate source version + content hash + immutable ACL version
  -> revoke the previous ACL version first
  -> old in-memory and persisted artifacts fail closed immediately
  -> purge every registered artifact carrying that ACL lineage
  -> persist source tombstone, purge result, and cleanup failures
```

Physical cleanup is defense in depth after revocation. A failed delete never
restores access to stale artifacts.

## Connector Contract

An observation contains only metadata:

- connector, source, team, and source type identifiers;
- immutable source version;
- expected previous source version for compare-and-swap replacement/reactivation;
- content hash;
- source ACL descriptor and immutable ACL version; and
- observation time.

Source bodies, prompts, credentials, and model responses are not written to the
connector lifecycle ledger.

The coordinator rejects:

- public-demo or unsigned connector administration;
- callers without `source_admin` or `security_admin` role;
- wildcard or unauthorized teams through the existing signed identity boundary;
- unscoped sources or sources without an ACL version;
- primary sources that claim derived ACL lineage;
- content changes without a new source version; and
- source or ACL changes that reuse an old ACL version; and
- stale or out-of-order observations that do not name the current source version.

Reusing a revoked ACL version is denied by the same default access policy used by
retrieval and generation.

## Registered Cleanup Coverage

Repositories automatically register versioned lineage for:

| Artifact | Cleanup behavior |
|---|---|
| Codebase index | Delete the index file; require rebuild |
| Evidence graph | Delete the mixed graph file if any registered source version is revoked; require rebuild |
| Memory scan and `latest` snapshot | Delete both registered scan files; require rescan |
| Context Trail / Context Pack / Prompt Preview / Memory Map | Delete the complete JSON/Markdown artifact directory |
| Requirement Case | Delete the SQLite case snapshot through the repository handler |
| Private connector source copy | Delete only when the connector registered a path below the private artifact root |

Mixed artifacts are deleted conservatively rather than rewritten in place. This
avoids retaining a denied source through summaries, edges, prompts, or cached
Markdown. A later authorized run rebuilds the artifact from currently readable
sources.

The lineage registry rejects paths outside the configured artifact root and
cannot register the artifact root or its own ledger for deletion.

## Lifecycle Evidence

Two metadata-only ledgers are stored under `pilot-security/`:

- `connector-source-lifecycle.json` records active/tombstoned source state and
  activation, replacement, reactivation, and deletion events; and
- `artifact-lineage.json` records exact artifact locators, ACL versions, cleanup
  status, timestamps, and errors.

The existing `access-revocations.json` remains the authorization source of truth.
Ledger writes use atomic file replacement and process-wide locks. A production
multi-instance deployment still requires an approved transactional/shared store.

Cleanup failures remain `cleanup_failed` with an operator-visible error. A
source/security administrator can run the controlled `cleanup_retry` action;
the source remains tombstoned and its ACL remains revoked throughout. The Pilot
must not report deletion complete until all registered artifacts are purged or
an approved retention exception exists.

## Verification

The connector lifecycle tests prove:

- private source-admin enforcement;
- idempotent unchanged observations;
- immutable source and ACL version rules;
- ACL refresh revokes the old version before cleanup;
- physical cascade across source copy, index, graph, memory scans, context
  artifacts, and Requirement Case;
- stale in-memory derived access remains denied after physical cleanup;
- an already-revoked source can still be physically cleaned by an authorized
  team source/security administrator;
- deletion tombstones and revocations survive service restart;
- out-of-root paths are rejected; and
- cleanup failures remain visible and a retry completes without restoring access.

## Remaining Pilot Gates

This slice does not change the real-source **No-Go** decision. Before a real
connector is enabled, the private extension still needs:

- an approved connector implementation, credential scope, polling/webhook
  strategy, retry/idempotency policy, and source allowlist;
- organization SSO/proxy, shared transactional lifecycle storage, and operator
  administration;
- approved private source storage plus retention/deletion SLA;
- explicit treatment of audit/evaluation metadata under the retention policy;
- redaction/DLP enforcement and a deletion verification job; and
- Security, Data/Privacy, source-owner, and technical-owner approval.

Private source copies must live below the approved artifact root and be registered
through `ConnectorLifecycleService.register_source_copy`. An extension that uses
another encrypted store must provide a reviewed cleanup handler with equivalent
fail-closed evidence.
