<!-- SPDX-License-Identifier: Apache-2.0 -->

# SME Reference Preparation

The JSON and YAML files in this directory are drafts, not approved evidence.

Approval workflow:

1. Freeze the scenario, output contract, source catalog, and golden profile.
2. BA/TL/QA/OPS SMEs review the request without seeing either benchmark arm.
3. Replace every `SME:` placeholder with the accepted output and stable source
   ids from the frozen catalog.
4. Validate the JSON against `LeadershipBenchmarkOutput`.
5. Calculate SHA-256 over the exact UTF-8 JSON bytes.
6. Copy the manifest template to a private approved-evidence location.
7. Set `status: approved`, named `reviewer`, ISO-8601 `approved_at`, the final
   relative JSON filename, and `reference_sha256`.
8. Run the loader/benchmark; it rejects drafts, missing approval identity,
   scenario/contract mismatches, path traversal, and hash mismatch.

Do not commit a real organization SME identity, private source text, or company
golden answer to the public repository.

## Provider Pricing Preparation

`provider-pricing.manifest.template.yaml` is also a rejected draft. Before cost
can be measured, the evidence owner must copy it into the approved private
package and record:

- the exact provider and resolved model returned by both benchmark arms;
- ISO currency and input/output price per one million tokens;
- the pricing effective time;
- approver and approval time; and
- a versioned internal or public source reference.

Set `status: approved` only after review. Cost remains `not_measured` when the
provider returns only total tokens because different input and output rates
cannot be applied honestly without the separate counts.
