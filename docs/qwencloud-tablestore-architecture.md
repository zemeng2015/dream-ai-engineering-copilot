<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Durable Memory on Alibaba Cloud Tablestore

Decision date: 2026-07-12

## Decision

DREAM's Qwen Cloud competition runtime stores experience memory in Alibaba
Cloud Tablestore Wide Column in `ap-southeast-1`. We rejected SQLite on
Function Compute `/tmp` because warm-instance persistence is not durable, and
rejected SQLite on NAS because a shared file does not make the existing
multi-row state transition atomic. RDS Serverless is technically valid but
adds a connection pool, VPC, minimum storage, wake-up, and migration surface
that is unnecessary for this submission.

The deployed resources are deliberately small:

| Resource | Configuration |
|---|---|
| Instance | `dreammem`, CU mode, high-performance, ZRS |
| Table | `dream_experience_v1` |
| Primary key | `scope_id STRING`, `record_id STRING` |
| Retention | TTL `-1`, max versions `1` |
| Capacity | Reserved read `0`, reserved write `0` |
| Atomicity | Local transactions enabled at table creation |

Tablestore documents local transactions as Read Committed, partition-scoped,
atomic read/write units protected by pessimistic locking. A transaction is
bounded to the first primary-key value and has a 60-second validity window.
See [local transactions](https://www.alibabacloud.com/help/en/tablestore/local-transactions)
and [table operations](https://www.alibabacloud.com/help/en/tablestore/table-operations).

## Data Model

`scope_id` is `sha256(team_id + NUL + user_id)`, prefixed with `scope-`. It
keeps one user's complete history in one Tablestore partition without placing
the original identifiers in the primary key.

`record_id` is one of:

- `m#<memory_id>` for an `ExperienceMemory` payload.
- `d#<decision_id>` for an `ExperienceDecisionRecord` payload.

Each row stores `record_type`, `status`, `updated_at`, and the canonical
Pydantic JSON payload. The table has no secondary or search index. The judge
workload is intentionally small, so a partition range scan is simpler, cheaper,
and easier to audit than an additional index.

## Atomic State Transition

For one `(team, user)` scope, capture runs as one local transaction:

1. Start a transaction using the hashed `scope_id` partition key.
2. Read all active memories in that partition.
3. Re-resolve the requested action against current state.
4. Mark the previous truth `superseded` when its value changed.
5. Insert the new active memory.
6. Append the immutable decision receipt.
7. Recount active memories and commit.

The same transaction boundary protects expiry, recall counters, and feedback.
Any exception aborts the transaction. A transaction store rejects every write
whose team or user differs from its bound partition.

This directly enforces the product invariant:

> For a given team, user, memory kind, and normalized key, exactly one current
> truth can remain active after a successful transition.

## Real Cloud Evidence

The committed sanitized receipt is
[`docs/assets/qwencloud-tablestore-proof-summary.json`](assets/qwencloud-tablestore-proof-summary.json).
It contains the Tablestore `DescribeTable` request ID, schema, reserved capacity,
timings, and invariant counts, but no credentials.

The first live round trip against `dreammem/dream_experience_v1` created one
memory and one decision, then reloaded the same value through a fresh service
object:

```text
backend=tablestore
durable=True
reloaded_count=1
decision_count=1
active_count=1
```

A barrier-synchronized 20-request contention run then wrote 20 different
values to one logical key:

```text
requests_succeeded=20
remember_actions=1
supersede_actions=19
memory_count=20
active_count=1
superseded_count=19
decision_count=20
```

All 20 transaction starts completed under Tablestore's partition lock. No
write, history row, or decision receipt was lost.

The deployed Function Compute path subsequently passed both remaining gates.
A 20-request HTTP burst completed with 20 successes, one active truth, 19
superseded histories, and 20 decision receipts in 7.494 seconds. A separate
Qwen-created memory was then recalled after the FC instance changed from
`c-6a537f3b-01459c63-95f653d85f5f` to
`c-6a537fcc-01459c63-9d10c45d0864` while the runtime source stayed at
`cb6255b7a1565a631daec6215bd146f495d97df8`.

The sanitized receipts are committed as
[`qwencloud-fc-http-contention-proof-summary.json`](assets/qwencloud-fc-http-contention-proof-summary.json)
and
[`qwencloud-fc-persistence-proof-summary.json`](assets/qwencloud-fc-persistence-proof-summary.json).
See [`qwencloud-fc-runtime-proof.md`](qwencloud-fc-runtime-proof.md) for the
end-to-end acceptance narrative and reproduction commands.

## Runtime Identity

Function Compute assumes `dream-qwencloud-fc-role`. The custom policy in
`deploy/alibaba/ram/dream-qwencloud-tablestore-data-policy.json` allows only
`GetRow`, `GetRange`, `PutRow`, and the three local transaction operations on
this table. FC injects temporary role credentials into the runtime environment;
the function does not receive the deployment RAM user's long-lived AccessKey.

The public proof surface exposes only:

- storage backend and transaction mode;
- FC instance ID;
- deployed build SHA;
- region, service, Qwen provider, and model.

It never returns Alibaba credentials, DashScope keys, or role tokens.

## Cost Boundary

The instance reserves zero read and write CUs and has no indexes. Charges are
limited to actual storage, requests, local-transaction operations, and small
public-network traffic during development. Current pricing is documented on
the [Tablestore pricing page](https://www.alibabacloud.com/en/product/table-store/pricing).
The resource is tagged `project=qwencloud-hackathon` for review and cleanup.
