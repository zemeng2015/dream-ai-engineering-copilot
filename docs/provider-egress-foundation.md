<!-- SPDX-License-Identifier: Apache-2.0 -->

# Provider Egress Foundation

Status: implemented and negatively tested in public core. This is an
application-level fail-closed contract, not evidence that Fannie or any other
organization has approved an endpoint, model, region, or data-processing term.

## Private Runtime Contract

Private mode permits deterministic/mock generation without external egress. A
live provider must be selected through deployment `config` and must be either
`openai-compatible` or `qwen-cloud`. Request/CLI parameters cannot select a live
provider directly, and LLM plugins remain blocked until an attested plugin
egress contract is implemented.

`DREAM_LLM_APPROVAL_FILE` must point to an absolute JSON file outside the public
checkout:

```json
{
  "schema_version": "provider-approval-v1",
  "approval_id": "security-change-1234",
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-5.4",
  "approved_by": "named-security-reviewer",
  "approved_at": "2026-07-10T12:00:00-04:00",
  "expires_at": "2026-08-10T12:00:00-04:00"
}
```

Provider construction fails unless provider, canonical HTTPS base URL, and
model match exactly and the time window is valid. The same manifest is reread
immediately before every invocation, so expiration, revocation by file removal,
or identity changes stop the next call without restarting the service.

The returned provider/model identity must also match the approved request. A
different response model is blocked before it enters the workflow.

## HTTP Boundary

The built-in OpenAI-compatible transport:

- rejects credentials, query/fragment values, encoded or ambiguous path
  segments, and insecure remote URLs;
- permits HTTP only for public local-loopback development;
- never follows HTTP redirects, preventing prompt and bearer-token forwarding
  to another target; and
- never includes provider HTTP error bodies in application exceptions.

Qwen retains its competition-specific Alibaba host validation in public mode;
private use would additionally require the same exact approval manifest.

## Evidence

Decisions append to
`artifacts/pilot-security/provider-egress-events.jsonl`. Evidence includes
status, reason code, provider/model, approval id, manifest hash, and a one-way
base-URL hash. It excludes API keys, approval-file paths, prompts, responses,
and raw endpoint URLs.

The JSONL ledger and lock are local-process foundations. A multi-instance Pilot
needs an approved shared append-only evidence store, retention policy, SIEM
export, and monitoring. Removing or expiring an approval stops the next
invocation; it cannot recall an already in-flight provider request.

Focused verification:

```powershell
python -m pytest -q `
  tests/test_provider_egress_policy.py `
  tests/test_openai_compatible_provider.py `
  tests/test_api_llm_provider.py `
  tests/test_qwen_cloud_provider.py
```

Tests cover missing/mismatched/expired approval, per-request recheck, response
model drift, private API/CLI override attempts, plugin import prevention,
insecure/ambiguous URLs, redirect denial, safe error handling, and public-mode
compatibility.

## External Gates and Limitations

This foundation does not provide:

- organization approval of GPT-5.4 or any other model;
- contractual validation of region, retention, no-training, legal/privacy, or
  data-residency terms;
- a signed manifest or enterprise change-management system—the deployment must
  protect the approval file with approved storage, identity, and change control;
- DNS pinning, firewall enforcement, private connectivity, proxy policy, or a
  deployment network allowlist;
- enterprise secret-manager integration or key rotation; or
- a shared multi-instance approval/evidence service with immediate distributed
  revocation; or
- availability, quota, cost, latency, or incident-response approval.

Real-source ingestion and live company-data prompts remain **No-Go** until the
organization approves these external controls and the complete Pilot data flow.
