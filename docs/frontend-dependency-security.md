<!-- SPDX-License-Identifier: Apache-2.0 -->

# Frontend Dependency Security Baseline

Status date: 2026-07-10
Branch: `codex/pilot-angular21-upgrade`

## Decision

The Angular 19 dependency blocker identified during the Pilot security audit is
technically remediated on this branch. The frontend now uses supported Angular
21 packages and the lower-dependency `@angular/build` toolchain.

This closes the repository dependency finding; it does not replace the normal
enterprise software/runtime approval for a Pilot deployment.

## Frozen Versions

| Dependency | Version |
|---|---:|
| Angular runtime/compiler | 21.2.18 |
| Angular CLI | 21.2.19 |
| `@angular/build` | 21.2.19 |
| TypeScript | 5.9.3 |
| RxJS | 7.8.2 |
| Zone.js | 0.15.1 |
| Local verification Node.js | 24.14.1 |

`package.json` declares the Angular-supported Node range:

```text
^20.19.0 || ^22.12.0 || ^24.0.0
```

See Angular's official [version compatibility](https://angular.dev/reference/versions)
and [update command](https://angular.dev/cli/update) documentation.

## Migration Path

The migration followed the supported one-major-at-a-time path:

```text
Angular 19.2.25 / CLI 19.2.27 / TypeScript 5.7.3
  -> Angular 20.3.26 / CLI 20.3.32 / TypeScript 5.9.3
  -> Angular 21.2.18 / CLI 21.2.19 / TypeScript 5.9.3
```

Angular schematics moved `DOCUMENT` from `@angular/common` to
`@angular/core` and added current schematic naming defaults. No product behavior
or route contract changed.

The final workspace replaces `@angular-devkit/build-angular` builders with:

- `@angular/build:application`;
- `@angular/build:dev-server`;
- `@angular/build:extract-i18n`; and
- `@angular/build:karma`.

This removed the vulnerable webpack-dev-server/sockjs/uuid chain while retaining
the existing Jasmine/Karma tests in a real headless Chrome browser. Angular 21
still supports Karma; a separate Vitest migration is optional and should not be
combined with this dependency remediation.

## Verification

Clean local verification recorded:

```text
npm audit --omit=dev: 0 vulnerabilities
npm audit: 0 vulnerabilities
Angular production build: passed
ChromeHeadless: 23/23 passed
Python: 243 passed, 1 skipped
Ruff: passed
pip check: passed
```

The production initial estimated transfer size changed from approximately
84.93 kB on the frozen Angular 19 leadership baseline to 88.70 kB on Angular 21,
remaining well below the configured 500 kB warning budget.

GitHub CI now installs the lockfile with Node 24.14.1 and treats both npm audits,
the production build, and ChromeHeadless tests as required job steps.

## Operating Rules

- Use `npm ci`, not an unlocked install, for CI and release verification.
- Do not use `ng serve` as the Pilot deployment server; deploy the verified
  production bundle behind the approved private boundary.
- Keep production and full-tree npm audits at zero unless Security records an
  explicit, time-bounded exception.
- Rerun build, browser tests, and both audits after every dependency update.
- Organization approval of Node, Angular, browser support, and dependency policy
  remains a Pilot gate even when the repository audit is clean.
