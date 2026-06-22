<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security Policy

DREAM is an early open-source project. Treat generated artifacts, local indexes,
knowledge packs, and logs as potentially sensitive when adapting the project to
real organizations.

## Supported Versions

Security fixes target the current `main` branch until formal releases are
published.

## Reporting a Vulnerability

For vulnerabilities, use GitHub private vulnerability reporting if it is enabled
for the repository. If private reporting is not available, open a minimal GitHub
issue requesting a private contact path and do not include secrets, exploit
details, credentials, customer data, or private company information in the issue.

## Sensitive Data Boundary

The public repository must not contain:

- real company data, tickets, PRs, runbooks, logs, endpoints, repository names,
  cloud paths, or deployment configuration
- credentials, tokens, cookies, API keys, private keys, or local environment
  files
- private knowledge packs or private customer context

Use `.env.example` for configuration shape only. Keep real `.env` files,
databases, generated artifacts, and private knowledge packs outside public
commits.
