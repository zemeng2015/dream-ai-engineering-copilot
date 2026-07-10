<!-- SPDX-License-Identifier: Apache-2.0 -->

# Leadership Paired A/B Benchmark

This benchmark measures the effect of DREAM context without changing the model,
request, or output contract. It is provider-neutral and uses only the synthetic
DemoCorp Forecast Platform scenario.

## Fairness Contract

Both arms use:

- the same provider instance and resolved model;
- the same organization request;
- the same `engineering-decision-v1` JSON schema;
- the same generation instructions; and
- the same process and measurement code.

The only intentional variable is the source catalog:

- **Stateless:** no organization sources;
- **DREAM:** the fixed Requirement Case evidence catalog, including only claims
  admitted by the governed-memory retrieval policy.

The runner aborts if the provider or resolved model differs between arms. The
report records SHA-256 hashes for the request, contract, prompts, and raw
outputs.

## Metrics

The deterministic evaluator reports:

- valid and invalid source citations;
- impact recall against the scenario's expected code set;
- critical-question recall against the role-specific golden set;
- expected test coverage;
- incident/Jira/PR history coverage;
- unsupported output items;
- wall-clock latency; and
- provider-reported token usage when available.

Cost is reported as `not_measured` until an approved, versioned provider/model
pricing manifest is supplied. The resolved provider/model must match exactly,
and the provider must return separate input and output token counts. Human edit
distance is `not_measured` unless the run receives an approved, hash-verified
SME reference manifest.

## CI Harness Validation

Run the deterministic fixture:

```powershell
python scripts/run_leadership_ab_benchmark.py --provider fixture
```

This proves the paired harness, output parsing, invariants, metrics, and report
generation. Its report is always labeled `harness_validation` and must never be
presented as model-quality, productivity, or ROI evidence.

## Live Same-Model Evidence

Configure an approved OpenAI-compatible endpoint in the backend environment,
then run three paired repetitions (six provider calls):

```powershell
$env:OPENAI_COMPATIBLE_API_KEY="<approved-secret>"
$env:OPENAI_COMPATIBLE_BASE_URL="https://<approved-endpoint>/v1"
$env:OPENAI_COMPATIBLE_MODEL="gpt-5.4"
python scripts/run_leadership_ab_benchmark.py --provider openai-compatible --model gpt-5.4
```

`gpt-5.4` is the current local Leadership test target. This records a technical
choice, not Fannie provider approval; production/Pilot use still requires the
organization-approved endpoint, deployment identifier, data flow, and pricing
evidence.

Optionally supply an approved SME manifest. The manifest must name the reviewer,
approval time, scenario/contract, relative reference JSON path, and exact
SHA-256. Draft or mismatched manifests are rejected:

```powershell
python scripts/run_leadership_ab_benchmark.py `
  --provider openai-compatible `
  --repetitions 3 `
  --sme-reference-manifest C:\approved\async-status-sme-reference.yaml `
  --pricing-manifest C:\approved\provider-pricing.yaml
```

The suite alternates `stateless -> dream` and `dream -> stateless` call order to
reduce ordering bias. It reports per-run evidence plus mean, median, minimum,
and maximum for each measured metric.

Outputs are written to `artifacts/leadership-benchmark/`. A report may be cited
as live model evidence only when:

1. `evidence_tier` is `live_model_evidence`;
2. all four same-provider/model/request/contract checks are true;
3. both outputs pass the JSON contract;
4. the exact provider/model and run limitations are shown; and
5. no real Fannie data or unauthorized endpoint was used.

If a pricing manifest is supplied, the report also stores its SHA-256, approval
metadata, effective date, exact rates, and the raw provider token breakdown for
each arm. A provider/model mismatch aborts the benchmark instead of silently
applying the wrong price.

For leadership material, retain the individual runs and suite distribution. Do
not turn a single synthetic completion into a production ROI claim.

## Current Evidence Status

- The deterministic harness is implemented and covered by automated tests.
- The public SME files under `examples/leadership-benchmark/` are preparation
  templates only and are intentionally rejected as approved evidence.
- The public pricing manifest is also a draft template; zero placeholder rates
  are not cost evidence.
- The current fixture result shows the metric pipeline working, including honest
  zeroes where the retrieved context does not contain expected tests.
- A provider-neutral live-model report has not yet been approved or recorded in
  this product branch.
- The Qwen competition benchmark is a separate competition asset and is not the
  Fannie leadership evidence baseline.
