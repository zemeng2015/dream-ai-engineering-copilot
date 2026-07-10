<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Experience Memory Benchmark

DREAM's Track 1 benchmark measures whether a Qwen-powered curator can turn
natural-language observations into governed cross-session memory, then recall
the right memory without leaking superseded, expired, forgotten, or
budget-excluded values.

## Run Configuration

- Run ID: `20260710T045527Z`
- Provider: `qwen-cloud`
- Model: `qwen3.7-plus`
- Temperature: `0`
- Cases: `24`
- Curator decisions: `37`
- Qwen token usage: `28,730` total (`24,872` prompt, `3,858` completion)
- Runtime: `122.365` seconds
- Dataset: `examples/experience-benchmark/scenarios.yaml`
- Full report: `docs/assets/qwen-experience-memory-benchmark-report.json`

No credentials, workspace URL, or secret-bearing model input is included in the
public report.

## Results

| Metric | Result |
|---|---:|
| Lifecycle cases passed | 24 / 24 |
| Qwen curator proposal accuracy | 100.0% |
| Governed action accuracy | 100.0% |
| Critical memory recall | 100.0% |
| Forbidden memory leak rate | 0.0% |
| Token-budget compliance | 100.0% |
| Semantic payload diagnostic | 100.0% |
| Exact canonical key diagnostic | 51.3% |
| Weighted score | 100.0 / 100 |
| Stateless carryover recall | 0.0% |

All five scenario families passed every lifecycle case:

- 8 cross-session preference cases
- 6 conflict and supersession cases
- 4 TTL or explicit-forget cases
- 4 limited-context token-budget cases
- 2 duplicate or ignore cases

## Scoring Contract

A lifecycle case passes when:

1. Qwen proposes the expected `remember`, `supersede`, `forget`, or `ignore`
   operation.
2. DREAM's deterministic governance layer resolves the expected final action.
3. The required memory identity is present in budgeted recall.
4. No forbidden old, expired, forgotten, or low-priority value is recalled.
5. Estimated context use remains within the requested token budget.

Payload and canonical-key metrics are deliberately reported separately. Qwen
can preserve the correct meaning while choosing a longer value or a different
snake_case key. Semantic payload coverage contributes 10% of the weighted score;
exact canonical-key accuracy is an unweighted diagnostic and does not turn a
correct memory lifecycle into a failed case.

The weighted score is:

```text
15% curator proposal accuracy
15% governed action accuracy
10% semantic payload diagnostic
35% critical memory recall
15% forbidden-memory safety
10% token-budget compliance
```

## Reproduction

Validate lifecycle mechanics without an external model call:

```powershell
python scripts/qwencloud_experience_memory_benchmark.py --policy deterministic
```

Run the same natural-language cases through Qwen Cloud:

```powershell
python scripts/qwencloud_experience_memory_benchmark.py --policy qwen-cloud
```

Recompute scoring from a captured report without another model call:

```powershell
python scripts/qwencloud_experience_memory_benchmark.py `
  --rescore artifacts/qwencloud-experience-benchmarks/<report>.json
```

## Limitations

- The cases are synthetic and do not establish production effectiveness.
- One deterministic Qwen completion was used per curator step.
- Token-based semantic scoring does not replace human evaluation.
- The stateless comparison is intentionally narrow: without persistent state,
  cross-session carryover recall is zero by definition.
