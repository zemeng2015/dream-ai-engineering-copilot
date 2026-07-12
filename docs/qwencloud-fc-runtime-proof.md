<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen + Function Compute + Tablestore Runtime Proof

Acceptance date: 2026-07-12

## Frozen Runtime

| Field | Verified value |
|---|---|
| Public URL | `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run` |
| Runtime source | `cb6255b7a1565a631daec6215bd146f495d97df8` |
| Region | `ap-southeast-1` |
| Compute | Alibaba Cloud Function Compute custom runtime |
| Model | `qwen3.7-plus` through `qwen-cloud` |
| Memory store | `dreammem/dream_experience_v1` on Tablestore |
| Transaction | Partition-local transaction |
| FC identity | `dream-qwencloud-fc-role` with temporary credentials |

The live `/health` payload and response headers expose the source SHA, FC
instance ID, storage backend, transaction mode, provider, model, service, and
region. They do not expose API keys, AccessKeys, or role tokens.

## Real Qwen Receipt

The final seed request asked DREAM to remember that database migrations must be
run and verified before shifting production traffic. The public FC endpoint
called the official Singapore DashScope host and Qwen returned a `remember`
decision:

```text
provider=qwen-cloud
model=qwen3.7-plus
action=remember
memory_key=pre_migration_verification
total_tokens=780
qwen_latency_ms=2352
provider_request_id=f2d4a51b-3e0a-9734-ac6a-20bf45dac397
```

The receipt stores SHA-256 hashes of the request and response, request timing,
token usage, and the provider request ID. It never stores the DashScope key.

## Cross-Instance Persistence

The seed operation wrote memory `experience-memory-6c31f019d6da` and decision
`experience-decision-ac20b106c383` through Function Compute's temporary role.
After rebuilding and redeploying the same source commit, Function Compute
replaced the runtime instance:

```text
seed_instance=c-6a537f3b-01459c63-95f653d85f5f
verify_instance=c-6a537fcc-01459c63-9d10c45d0864
instance_changed=true
```

The new instance reloaded the same memory payload, decision ID, request hash,
response hash, and provider request ID, then recalled the memory for a new
session. This rules out process memory and `/tmp` as the source of persistence.

The machine-readable receipt is
[`docs/assets/qwencloud-fc-persistence-proof-summary.json`](assets/qwencloud-fc-persistence-proof-summary.json).

## Public HTTP Contention

An initial 20-request burst exposed a real deployment flaw: the function was
capped at reserved concurrency `1`, so FC returned HTTP 429. We did not count
that run as evidence. The runtime was changed to matching single-instance and
function concurrency of `20`, keeping one process-level Qwen limiter and a
bounded cost ceiling.

The repeated barrier-synchronized burst then passed through the complete public
path: HTTP trigger, Function Compute, temporary execution role, Tablestore SDK,
and local transaction.

```text
requests_attempted=20
requests_succeeded=20
http_errors=0
remember_actions=1
supersede_actions=19
active_count=1
superseded_count=19
decision_count=20
duration_seconds=7.494
max_request_latency_ms=7485
```

The machine-readable receipt is
[`docs/assets/qwencloud-fc-http-contention-proof-summary.json`](assets/qwencloud-fc-http-contention-proof-summary.json).

## Reproduce

The two-phase verifier intentionally refuses to pass while the FC instance ID
is unchanged:

```powershell
$baseUrl = "https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run"
$sha = "cb6255b7a1565a631daec6215bd146f495d97df8"

python scripts/qwencloud_fc_persistence_proof.py seed `
  --base-url $baseUrl `
  --expected-build $sha

# Rebuild and redeploy the same source commit to replace the FC instance.

python scripts/qwencloud_fc_persistence_proof.py verify `
  --base-url $baseUrl
```

The Tablestore-only 20-way proof remains separately reproducible with
`scripts/qwencloud_tablestore_proof.py`. Function Compute concurrency behavior
follows Alibaba Cloud's official guidance for
[single-instance concurrency](https://www.alibabacloud.com/help/en/functioncompute/fc/configure-the-concurrency-of-a-single-instance)
and
[reserved concurrency](https://www.alibabacloud.com/help/en/functioncompute/fc/developer-reference/api-fc-2023-03-30-struct-putconcurrencyinput).
