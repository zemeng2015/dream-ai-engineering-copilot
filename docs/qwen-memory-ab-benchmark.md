# Qwen + DREAM Paired Memory Benchmark

This report makes the hackathon benchmark reproducible without publishing
credentials, the dedicated Model Studio workspace URL, or raw model outputs.
The canonical machine-readable summary is
`docs/assets/qwen-memory-ab-benchmark-summary.json`.

## Run Configuration

- Run ID: `20260709T215947Z`
- Provider: `qwen-cloud`
- Model: `qwen3.7-plus`
- Cases: seven synthetic engineering cases
- Temperature: `0`
- Retrieval cutoff: `12`
- Comparison: no organization evidence versus DREAM-retrieved evidence

Both arms used the same model, temperature, output contract, requests, and
deterministic scorer. Call order alternated by case. Six requests came verbatim
from existing `examples/requirement-requests/` fixtures; the seventh was a
neutral idempotency request that did not reveal expected identifiers.

## Aggregate Results

| Metric | Stateless Qwen | Qwen + DREAM | Delta |
|---|---:|---:|---:|
| Deterministic reference score | 25.3 | 48.7 | +23.4 |
| Domain/risk recall | 18.8% | 43.8% | +25.0 pp |
| Expected source recall | 0.0% | 40.2% | +40.2 pp |
| Valid references | 0 | 105 | +105 |
| Unsupported references | 0 | 0 | 0 |

DREAM scored higher in all `7/7` paired cases. The median score delta was
`+23.2`; the exact paired permutation test gave `p=0.0156`.

## Paired Cases

| Case | Exact path Recall@12 | Baseline | DREAM | Delta |
|---|---:|---:|---:|---:|
| async-status-tracking | 40.0% | 23.5 | 46.7 | +23.2 |
| output-collection-idempotency | 54.5% | 23.0 | 61.5 | +38.5 |
| task-config-validation | 30.0% | 25.0 | 50.5 | +25.5 |
| partial-execution-recovery | 8.3% | 28.7 | 36.5 | +7.8 |
| workflow-versioning | 50.0% | 27.5 | 47.1 | +19.6 |
| operator-retry-action | 25.0% | 26.7 | 41.5 | +14.8 |
| large-output-preview | 41.7% | 22.5 | 57.1 | +34.6 |

Mean exact retrieval Recall@12 was `35.6%`. The low recall is a measured
bottleneck, not a hidden success condition.

## Scoring

The deterministic reference score combines exact recall of profile-defined
concepts and risks (35%), expected source identifiers (35%), expected roles
(15%), and required output sections (15%). Unsupported references incur a
four-point penalty each, capped at 20 points. A citation receives credit only
when that source appeared in the evidence supplied to that arm; the full corpus
is used only to distinguish unseen-real references from fabricated ones.

Retrieval is evaluated separately using exact canonical path or ID Recall@12,
Precision@12, and nDCG@12. The generation score does not substitute for these
retrieval metrics.

## Reproduction

```powershell
python scripts/qwencloud_memory_ab_benchmark.py --output-dir artifacts/qwencloud-benchmarks
python -m pytest -q tests/test_qwencloud_memory_ab_benchmark.py tests/test_engineering_memory_ranking.py tests/test_retriever.py
```

The benchmark requires a locally configured Qwen workspace key and matching
dedicated regional endpoint. Neither value belongs in source control.

## Limitations

- This is a seven-case synthetic benchmark, not a production-effectiveness claim.
- One deterministic completion per arm does not estimate sampling variance.
- Exact-term scoring favors explicit references and does not measure semantic equivalence.
- Eleven recovered arm outputs lack latency and token sidecars, so latency and token use are not comparative claims.
- Exact retrieval Recall@12 remains a bottleneck and bounds achievable gains.
- Human review remains required before treating generated artifacts as correct.
