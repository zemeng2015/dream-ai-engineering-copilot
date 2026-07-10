<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pilot Security Foundation

Status: implemented and tested on `codex/pilot-security-foundation`; this is a
public-core security contract, not approval to ingest organization data.

## Security Invariants

- `public-demo` accepts only `public_demo / local_demo` resources.
- `private-extension` requires a named authenticated principal, explicit team
  membership, an allowed action role, a versioned source ACL, and a matching
  principal or group.
- Missing identity, team, role, ACL scope, ACL version, or ACL subject fails
  closed.
- `security_admin` does not bypass source ACLs.
- Unmarked API routes are automatically disabled in private mode.
- Only `/health/live` is anonymous; it returns `{"status":"ok"}` and no runtime,
  provider, model, source, or configuration details.
- FastAPI `/docs`, `/redoc`, and `/openapi.json` metadata endpoints are disabled
  in private mode.
- Local file-path PR inputs are disabled in private mode.
- Access metadata propagates through documents/chunks, code indexes/files/
  symbols/concepts/tests, graph nodes, MemoryClaims, Requirement evidence,
  Context Trails/Packs, prompt previews, and PR artifacts.
- Derived Case/PR artifacts receive an ACL no broader than every source actually
  used. The creating principal is retained, while groups are limited to the
  intersection of the requested workspace ACL and source ACLs.
- Derived artifacts retain every underlying `source_acl_version`. A persistent,
  team-scoped revocation ledger denies both the original source and every
  derived artifact on the next policy decision.
- Private live-model calls must use the deployment-configured provider and an
  unexpired exact endpoint/model approval outside the public checkout. Approval
  is rechecked before every invocation; redirects and response identity drift
  fail closed.

## Signed Identity Boundary

Private API routes do not trust plain caller headers. An approved authentication
proxy must sign this canonical payload with HMAC-SHA256:

```text
principal_id
sorted,comma-separated team_ids
sorted,comma-separated group_ids
sorted,comma-separated roles
unix_timestamp
request_id
uppercase HTTP method
request path
```

Required headers:

```text
X-DREAM-Principal-Id
X-DREAM-Team-Ids
X-DREAM-Roles
X-DREAM-Identity-Timestamp
X-DREAM-Identity-Signature
X-Request-Id
```

Optional headers are `X-DREAM-Group-Ids` and `X-DREAM-Identity-Key-Id`.
Wildcard teams are forbidden. The signature is bound to request id, method, and
the exact raw request target (path plus query string), so it cannot be replayed
against another target. The default replay window is 60 seconds and can only be
configured between 10 and 300 seconds.

Private Requirement Case answer and waiver audit actors are derived from the
verified principal. Client-supplied actor labels cannot replace that identity.

Deployment configuration must come from the approved secret manager:

```powershell
$env:DREAM_CONFIG_FILE = 'C:\approved-private\dream.yaml'
$env:DREAM_IDENTITY_HEADER_SECRET = '<at-least-32-byte-secret>'
$env:DREAM_IDENTITY_HEADER_KEY_ID = 'pilot-key-2026-01'
$env:DREAM_IDENTITY_MAX_CLOCK_SKEW_SECONDS = '60'
```

The HMAC contract authenticates the proxy assertion; it does not replace
enterprise SSO. The proxy must authenticate through the organization-approved
OIDC/SAML mechanism, strip all inbound DREAM identity headers, map current group
and team membership, sign fresh assertions, and prevent direct network access to
the DREAM API.

## Private API Surface

ACL-enforced private routes currently cover:

- bounded PR Review;
- codebase search, concepts, file listing, and authorized file content;
- graph search, explain, and neighbors;
- Context Trail, Context Pack, prompt preview, and memory report;
- approved MemoryClaim search and context card; and
- Requirement Case create/analyze/read, impacts, questions, human decisions,
  brief, Jira draft/context, and readiness.

The private guard intentionally blocks codebase/graph build, Knowledge Intake,
Memory scan/review/conflict administration, TestGen, Audit/Eval administration,
legacy requirement draft, Qwen showcase, and all other unmarked routes. Those
surfaces remain available in `public-demo`; they must receive action-specific
authorization, connector ACL propagation, and negative tests before being
enabled in `private-extension`.

## Verified Negative Cases

Automated tests prove:

- unsigned, expired, tampered, wildcard-team, and wrong-key assertions fail;
- missing identity configuration fails closed;
- cross-team and cross-group Requirement Cases are hidden;
- denied chunks, code files, graph nodes, graph neighbors, graph paths, and
  MemoryClaims are excluded;
- denied source names and content do not enter Requirement evidence, Jira
  output, prompt preview, or Context Trail; and
- a broad workspace ACL is narrowed when its selected sources have a narrower
  ACL; and
- revoking a source ACL version invalidates both source retrieval and a derived
  Case/PR artifact carrying that lineage.

Run the focused security suite:

```powershell
python -m pytest `
  tests/test_access_policy.py `
  tests/test_signed_proxy_identity.py `
  tests/test_api_private_security.py `
  tests/test_acl_aware_retrieval.py `
  tests/test_access_revocation.py `
  tests/test_private_requirement_acl_flow.py
```

## Still Required Before Real Sources

This foundation does not yet prove:

- organization-approved SSO/proxy deployment and network isolation;
- connector-side automatic ACL/revocation synchronization or identity/group
  lifecycle integration;
- deletion cascades for source bodies, indexes, prompts, caches, and artifacts;
- action-specific authorization for currently blocked administration routes;
- organization-approved DLP taxonomy and deployment, binary/OCR/malware
  inspection, private storage, retention/deletion, approved audit export
  operations, incident
  response, data residency, or provider approval; or
- Security/Data/source-owner approval of the exact Pilot data flow.

### Frontend Dependency Remediation

The 2026-07-10 security audit initially found 7 production findings and 28 total
findings in the Angular 19 dependency tree. The isolated Angular upgrade slice
now uses Angular 21 and `@angular/build`; both production and full npm audits
report zero vulnerabilities, the production build passes, and all 23
ChromeHeadless tests pass. See
[Frontend Dependency Security Baseline](frontend-dependency-security.md).

Repository remediation does not replace organization approval of the exact
Node/Angular/browser runtime and dependency policy before Pilot deployment.

`source_acl_version`, derived lineage, and the core revocation ledger enforce
fail-closed invalidation once a version is revoked. The provider-neutral
connector lifecycle foundation now consumes source changes, revokes old versions
before cleanup, and purges registered source/derived artifacts. Production
connector implementation, shared transactional storage, and organization
deletion approval remain open. See
[Connector Source Lifecycle Foundation](connector-lifecycle-foundation.md).
Until these items are approved and tested, real-source ingestion remains
**No-Go**.

The public core now also includes a versioned deterministic DLP enforcement
foundation at the text boundaries currently used by source loading, indexing,
Requirement Case persistence, prompt dispatch, and model response handling. See
[DLP Enforcement Foundation](dlp-enforcement-foundation.md). It reduces accidental
text leakage risk but does not satisfy the enterprise DLP gate by itself.

The provider egress foundation prevents request-level live-provider overrides,
requires exact time-bounded provider/endpoint/model approval, blocks redirects,
and writes metadata-only decisions. Organization endpoint approval, network
egress enforcement, retention/no-training terms, and data residency remain
external gates. See [Provider Egress Foundation](provider-egress-foundation.md).

The offline Pilot evidence exporter now creates a team-scoped, metadata-only,
checksummed v2 bundle from eleven control sections without enabling private
Audit/Eval API administration. Runtime signed-identity and access-policy
decisions are now persisted with fail-closed writes; untrusted identity
rejections are aggregated at deployment scope. The bundle remains partial
because its local sources do not share one global transaction or signed custody.
See [Security Decision Evidence Foundation](security-decision-evidence-foundation.md)
and
[Pilot Evidence Export Foundation](pilot-evidence-export-foundation.md).

A detached Ed25519 receipt can now authenticate a verified bundle against a
public key held outside both the checkout and artifact root. Signing fails on an
invalid bundle and receipt verification fails on bundle, manifest, receipt, key
or key-id drift. This remains a local custody foundation; organization key
approval, KMS/HSM integration, revocation and immutable registration are still
required. See [Pilot Evidence Custody Foundation](pilot-evidence-custody-foundation.md).
