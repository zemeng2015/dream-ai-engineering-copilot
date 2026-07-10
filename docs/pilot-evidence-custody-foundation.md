<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pilot Evidence Custody Foundation

Status: implemented and tested as an offline Ed25519 detached-signature
foundation. It authenticates a bundle against a separately trusted public key;
it does not provide organization key approval, HSM custody, legal
non-repudiation or a compliance certification.

## Trust Model

The evidence bundle verifier proves internal consistency. A complete attacker
replacement can also replace internal hashes, so the root must be anchored
outside the bundle. DREAM can now sign that root and the exact manifest bytes
with an Ed25519 private key.

The detached receipt binds:

- bundle schema version, id and root SHA-256;
- exact `manifest.json` SHA-256;
- Ed25519 public-key fingerprint;
- hashed key id, signer id and signing reason; and
- timezone-aware signing time.

The signature covers every field above. The receipt remains outside the bundle,
so the v1/v2 exact-file-set contracts do not change.

The private key and trusted public key must use absolute paths outside both the
public checkout and configured artifact root. Co-locating the trust anchor with
mutable evidence would allow one compromised boundary to replace both. Symlink
key paths, non-Ed25519 keys, unsafe output paths and receipt overwrite attempts
fail closed.

## Sign a Verified Bundle

Supply an organization-controlled Ed25519 PEM key. The local command is an
operating foundation; production should prefer the approved KMS/HSM or artifact
signing service rather than a long-lived filesystem private key.

```powershell
$env:DREAM_EVIDENCE_SIGNING_KEY_PASSWORD = '<from-approved-secret-manager>'

dream audit sign-bundle `
  --bundle C:\approved-artifacts\pilot-evidence\<bundle-id> `
  --expected-root-sha256 <root-returned-by-reviewed-export> `
  --private-key C:\approved-private\custody\evidence-ed25519-private.pem `
  --private-key-password-env DREAM_EVIDENCE_SIGNING_KEY_PASSWORD `
  --key-id pilot-custody-2026-01 `
  --signer pilot-operator `
  --reason "weekly Pilot evidence freeze"
```

The expected root is mandatory: signing must be an explicit decision about the
already reviewed exporter result, not approval of whichever bytes happen to be
at a path. DREAM verifies the bundle/root before and after constructing the
signature and writes no receipt if they drift.

Unencrypted PEM is supported for isolated development tests, but it is not the
recommended enterprise operating mode. The command first runs full internal
bundle verification. An invalid bundle cannot be signed. The default write-once
sidecar is:

```text
<artifact-root>/pilot-evidence/<bundle-id>.signature.json
```

Raw key id, signer and reason are not written; their deterministic SHA-256
digests are pseudonymous evidence and must still be handled as sensitive.

## Verify Against a Trusted Key

The public key must be obtained from an independently controlled and approved
channel, not copied from the evidence package being tested.

```powershell
dream audit verify-signature `
  --bundle C:\approved-artifacts\pilot-evidence\<bundle-id> `
  --receipt C:\approved-artifacts\pilot-evidence\<bundle-id>.signature.json `
  --public-key C:\approved-private\trust\evidence-ed25519-public.pem `
  --expected-key-id pilot-custody-2026-01
```

Verification fails on internal bundle tamper, manifest drift, receipt metadata
tamper, signature corruption, wrong public key, wrong expected key id, invalid
key type, symlink/co-located key or malformed receipt. The command exits nonzero
on failure.

## Remaining Enterprise Gates

The public core does not supply:

- organization key issuance, approval, rotation, revocation or compromise
  response;
- KMS/HSM/managed signing integration or separation-of-duty enforcement;
- trusted timestamp authority, transparency log or immutable receipt registry;
- certificate identity, legal non-repudiation or custody attestation;
- shared transactional audit storage, retention/legal hold or SIEM/GRC export;
  or
- an approved evidence handling and investigation procedure.

An enterprise Pilot must trust the public key fingerprint and operating process
through a channel independent of the bundle and sidecar. A cryptographically
valid local signature alone is not evidence that the organization approved the
signer, data, model, Pilot or result.
