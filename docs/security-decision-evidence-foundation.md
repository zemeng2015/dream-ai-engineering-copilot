<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security Decision Evidence Foundation

Status: implemented and tested for the private-extension Pilot boundary. This
is metadata-only local evidence, not an enterprise identity system, SIEM or
compliance archive.

## Runtime Decisions Recorded

The signed proxy identity boundary writes an event for every non-anonymous
private assertion it accepts or rejects. The deliberately data-free liveness
route remains exempt. A successfully verified assertion records only
deterministic hashes of the trusted principal, team set, request id, request
target and method, plus subject counts, timestamp, status and reason code.

Rejected assertions never retain principal or team values from inbound headers.
Those values are attacker-controlled until the signature is verified. Rejection
events therefore contain only deployment-safe status/reason metadata and hashed
request shape. Identity configuration failures are recorded when the local
evidence store is available.

`DefaultAccessPolicy.decide()` records every decision when DREAM is configured
in `private-extension` mode. Each event contains:

- allow/deny and bounded reason code;
- action and runtime mode;
- hashed team, principal, request and resource identifiers;
- classification and ACL scope when a resource descriptor exists; and
- hashed source ACL versions.

No source body, prompt, response, credential, raw principal/team/request id,
resource path or request target is written to either ledger.

## Failure Contract

Decision evidence is part of the private control boundary, not best-effort
telemetry. If a configured identity decision cannot be persisted, authentication
fails with a generic configuration error. If an access-policy decision cannot be
persisted, the operation is denied. Underlying filesystem errors and private
values are not returned to the caller.

The local files are:

```text
<artifact-root>/pilot-security/identity-decisions.jsonl
<artifact-root>/pilot-security/access-policy-decisions.jsonl
```

They must remain inside the private artifact/control boundary. Direct public API
administration is not enabled.

## Evidence Bundle Semantics

Pilot evidence bundle v2 adds three sections:

| Section | Scope | Interpretation |
|---|---|---|
| Identity authentications | Team | Only successfully signed events attributable to the selected team |
| Identity rejections | Deployment | Aggregated status/reason counts; untrusted team headers are never used for attribution |
| Access-policy decisions | Team | Allow/deny decisions whose hashed team matches the selected export team |

The exporter hashes already-hashed identifiers again before emitting them. The
v2 manifest replaces the old persistence gaps with two explicit limitations:

- `identity_rejections_are_deployment_scoped`;
- `cross_source_snapshot_not_globally_atomic`.

The verifier continues to validate existing v1 bundles against their original
eight-section/two-gap contract. New exports use the eleven-section v2 contract.

## Remaining Enterprise Gates

The JSONL repositories use process-local locks and do not provide multi-process
serialization, remote durability, retention enforcement, legal hold, signed
custody, sequence continuity or a globally atomic snapshot with SQLite and the
other control ledgers. A production Pilot still needs:

- organization-approved SSO/proxy deployment and identity lifecycle;
- a shared append-only or transactional audit store with availability targets;
- approved retention, deletion, access-review and export authorization;
- an independently controlled signature/root registry and custody procedure;
- alerting/SIEM integration and abuse-rate operations; and
- load/capacity validation for high-volume retrieval decisions.

Until those gates are approved, this foundation proves that the application can
produce bounded runtime decision evidence; it does not certify the surrounding
enterprise control environment.
