<!-- SPDX-License-Identifier: Apache-2.0 -->

# Leadership Presentation Release Process

The release manifest binds one presentation candidate to its Git state, source
snapshot, critical product files, evidence artifacts, and Angular production
bundle. It prevents a rehearsal or screenshot from silently drifting away from
the code later presented.

## Candidate vs Frozen

- `candidate_uncommitted`: checksums are valid for the current source bytes, but
  Git reports uncommitted changes or strict mode was not requested.
- `frozen`: strict mode was requested, Git is clean, the current branch is a
  product branch, and the preflight artifact itself records clean git hygiene.

`frozen` means the local presentation snapshot is reproducible. It does not mean
the system is production-ready, approved for real data, or supported by live
model/ROI evidence.

## Build a Candidate

```powershell
python scripts/build_leadership_release.py
python scripts/verify_leadership_release.py
```

The builder records:

- branch, commit SHA, and exact `git status --porcelain` lines;
- SHA-256 over every tracked or unignored untracked source file;
- individual checksums for the leadership code, scripts, UI profile, DFP profile,
  README, runbook, current-state, trust-boundary, Pilot and audit documents;
- checksums for preflight, rehearsal, and paired benchmark artifacts; and
- recursive Angular production-bundle hash and file count.

The verifier recomputes all of these values. Source, evidence, bundle, branch,
commit, or git-status drift fails verification.

## Freeze the Presentation Commit

After the product changes have been reviewed and intentionally committed:

```powershell
npm --prefix frontend run build
python -m pytest -q
python scripts/run_leadership_preflight.py `
  --require-frontend-bundle `
  --strict-git
python scripts/run_leadership_rehearsal.py
python scripts/build_leadership_release.py --strict
python scripts/verify_leadership_release.py
```

If rehearsal or any source changes after the manifest is built, rebuild and
verify the release. Do not manually edit hashes.

## Evidence Interpretation

The current synthetic suite may be attached to a frozen release as
`harness_validation`. The manifest must continue to warn when any of these are
missing:

- approved live-model suite;
- approved, hash-verified SME reference; or
- approved exact-provider/model pricing evidence.

Checksums provide integrity, not identity or non-repudiation. If the enterprise
Pilot requires signed releases, the private delivery process should sign the
manifest through the organization-approved artifact/signing service.

## Output

Generated files live under `artifacts/leadership-release/`:

- `leadership-release-manifest.json`
- `leadership-release-manifest.md`

These files are runtime evidence and are ignored by Git. Copy the verified pair
into the approved private presentation/evidence package when needed.
