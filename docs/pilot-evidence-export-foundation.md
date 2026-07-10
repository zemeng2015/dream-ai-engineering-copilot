<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pilot Evidence Export Foundation

Status: implemented and tested as an offline public-core control foundation. It
does not make the current local ledgers a production system of record or approve
the use of company data.

## Purpose and Boundary

The Pilot evidence bundle gives a reviewer one immutable, machine-verifiable
snapshot of the control evidence currently distributed across DREAM's local
SQLite database and metadata ledgers. An export is limited to one explicitly
confirmed team. It contains hashes, counts, timestamps, enums, scores and other
bounded metadata; it intentionally excludes source bodies, prompts, model
responses, comments, paths, user names, team names and other arbitrary text.
Identifier digests are deterministic pseudonyms, not anonymization: low-entropy
values may still be guessable and equality can be correlated across bundles.
Export authorization and storage must therefore treat the bundle as sensitive
operational evidence.

The command is deliberately offline. The private API's Audit/Eval administration
routes remain disabled. Exporting a bundle therefore does not expand the remote
administration surface or create an external side effect.

## Included Evidence

| Section | Scope | Source |
|---|---|---|
| Audit runs | Team | Audit SQLite database |
| Human ratings | Team, joined through the team's audit runs | Audit SQLite database |
| Evaluation summaries | Team | Audit SQLite database |
| Access revocations | Team | Revocation ledger |
| Connector lifecycle | Team | Connector lifecycle ledger |
| Artifact lineage | Team | Artifact lineage registry |
| DLP decisions | Team | DLP decision ledger |
| Provider egress decisions | Deployment | Provider egress ledger |
| Identity authentications | Team | Signed identity decision ledger |
| Identity rejections | Deployment | Aggregated signed identity rejection evidence |
| Access-policy decisions | Team | Default access-policy decision ledger |

Provider events are deployment-scoped because the current provider decision
record does not carry a team identifier. The manifest marks that scope instead
of presenting those events as team-attributable evidence.

The bundle status remains `partial_control_evidence`. New exports use v2, whose
mandatory limitations are:

- `identity_rejections_are_deployment_scoped`;
- `cross_source_snapshot_not_globally_atomic`.

Identity rejections cannot be attributed to an asserted team until its signature
is trusted, so they are aggregated at deployment scope. The verifier rejects a
v2 manifest that hides either limitation. It also remains compatible with the
original eight-section v1 contract and its two historical persistence gaps.

## Create and Verify

Use the deployment's configured artifact and audit roots. The confirmation must
exactly match the selected team, and operator/reason values are required. Only
their SHA-256 digests are written.

```powershell
dream audit export-bundle `
  --team pilot_team `
  --confirm-team pilot_team `
  --operator zack `
  --reason "weekly Pilot evidence review"
```

By default, a new write-once-by-the-exporter directory is created below
`artifacts/pilot-evidence/`. A custom `--output-root` must remain inside the
configured artifact root and cannot be placed inside the `pilot-security`
control directory.

The command returns the bundle path and `bundle_root_sha256`. Preserve that root
through a separate approved channel, then verify the bundle with it:

```powershell
dream audit verify-bundle `
  --bundle C:\approved-artifacts\pilot-evidence\<bundle-id> `
  --expected-root-sha256 <sha256-from-independent-channel>
```

Verification checks the versioned schema, fixed bundle naming/team-hash relationship,
exact file set, file sizes and hashes, section/source/scope/count contracts,
bounded metadata grammar, mandatory coverage gaps, and manifest root. Extra
files, altered records, unsafe arbitrary strings or keys, recomputed partial
checksums, and a mismatched out-of-band root fail verification.

## Integrity and Snapshot Semantics

The manifest root and section checksums provide integrity, not signer identity
or non-repudiation. Verification without `--expected-root-sha256` proves only
internal consistency: an attacker able to replace the complete bundle may also
replace its internal hashes. The optional
[Pilot Evidence Custody Foundation](pilot-evidence-custody-foundation.md) adds a
detached Ed25519 signature against a separately trusted public key. Organization
key approval, managed custody and immutable registration remain external gates.

Audit runs, ratings and evaluations are read in one SQLite read transaction.
Each JSON/JSONL ledger is accepted only when its pre-read and post-read file hash
is stable. These controls prevent torn reads within SQLite and detect a ledger
changing during its read, but the eleven v2 sections do not share one global
transaction or point-in-time sequence. The bundle is therefore a bounded
collection snapshot, not proof of globally atomic state.

Source snapshot hashes can cover a full deployment ledger even when exported
records are team-filtered. They are one-way integrity evidence and do not expose
the other team's records.

## Failure and Data-Handling Rules

- A malformed source, invalid timestamp, unstable ledger, path escape or unsafe
  output location fails closed.
- A failed build removes its newly created partial bundle directory.
- Existing bundle directories are never overwritten; filesystem permissions and
  independent-root verification are still required to detect later mutation.
- The verifier requires the exact twelve-file v2 set: eleven evidence sections
  and `manifest.json`; legacy v1 verification retains its exact nine-file set.
- Raw identifiers and upstream values already labelled as hashes are hashed
  again; the exporter never trusts an upstream string merely because its field
  name says `hash`.
- Empty and missing sources remain visible in manifest coverage rather than
  being silently omitted.

## Still Required for an Enterprise Pilot

Before this can be treated as production audit evidence, DREAM still needs:

- a shared transactional evidence store or an approved snapshot coordinator;
- approved retention, legal hold, deletion and export authorization policy;
- organization-approved signing keys, managed custody, rotation/revocation and
  an independently controlled immutable receipt/root registry;
- organization-approved operator identity, separation of duties and SIEM/GRC
  integration; and
- documented incident and evidence-custody procedures.

Until those controls and the broader Pilot gates are approved, the bundle is
useful engineering evidence for synthetic demonstrations and security review,
not a compliance certification.

See [Security Decision Evidence Foundation](security-decision-evidence-foundation.md)
for trust attribution, failure behavior and remaining runtime-ledger gates.
