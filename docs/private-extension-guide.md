<!-- SPDX-License-Identifier: Apache-2.0 -->

# Private Extension Guide

Use `examples/private-extension-template/` as the starting point for a private DREAM extension repository.

Recommended setup:

1. Copy the template into a private repository.
2. Pin the public DREAM package version.
3. Configure the built-in OpenAI-compatible provider with the exact approved
   endpoint/model; keep sample provider classes for contract development only.
4. Place private knowledge packs under that private repository.
5. Set `DREAM_CONFIG_FILE` to the private config file.
6. Set `DREAM_ARTIFACT_ROOT` outside the public DREAM checkout.
7. Copy and complete `config/provider-approval.example.json` outside the public
   checkout, then set `DREAM_LLM_APPROVAL_FILE` to its absolute path.
8. Run `dream config validate`, `dream config doctor`, and provider boundary tests.
9. Configure the audit SQLite path and artifact root on approved private storage;
   test `dream audit export-bundle` and retain its root digest through an
   independent approved channel before relying on Pilot evidence.
10. Verify the private runtime can append identity and access decisions under
    `<artifact-root>/pilot-security/`; an unavailable decision ledger fails
    identity/access operations closed by design.

Private mode rejects request-level live-provider selection and LLM plugins. Use
`config` at API/CLI generation surfaces so the deployment-owned provider is
selected. A future plugin-egress attestation contract must be implemented and
reviewed before enabling custom LLM plugins in private runtime.

The public repository should receive only generic interface or framework improvements. If a private workflow reveals a reusable enhancement, rebuild it with DemoCorp-style synthetic examples before contributing it to public core.

The current evidence bundle is an offline metadata-only foundation, not a
production audit archive. Its deployment-scoped identity rejections, local
multi-source snapshot semantics, process-local decision ledgers and unsigned
root are documented in `docs/security-decision-evidence-foundation.md` and
`docs/pilot-evidence-export-foundation.md`; the Pilot security owner must approve
or replace those boundaries.
