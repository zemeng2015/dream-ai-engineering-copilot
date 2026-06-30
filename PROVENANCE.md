<!-- SPDX-License-Identifier: Apache-2.0 -->

# Provenance and Company Import Policy

DREAM is maintained as a public personal/open-source upstream under the Apache
License, Version 2.0. The public upstream is intended to remain a clean,
reusable project skeleton for domain-aware engineering memory workflows.

## Public Repository Boundary

This repository contains original project code and synthetic DemoCorp examples
only. It does not include real company data, real internal project names, real
Jira tickets, real pull requests, real runbooks, real logs, real API endpoints,
real repository names, real cloud paths, credentials, or private deployment
configuration.

Company-specific knowledge packs, connectors, prompts, environment files,
deployment configuration, customer data, and generated operational artifacts
must live outside this public repository.

## Importing DREAM Into a Company

Recommended company import process:

1. Import from the public GitHub repository using a pinned commit, tag, or
   release.
2. Preserve `LICENSE`, `NOTICE`, and attribution notices.
3. Keep private company modifications in a company-controlled fork or private
   extension repository.
4. Do not upstream company-period modifications unless the employer explicitly
   authorizes the contribution and the change contains no confidential or
   proprietary material.
5. Keep company-specific knowledge packs, connectors, prompts, and deployment
   configuration private by default.

## Future Reuse

Future reuse should import only the public upstream project or public releases.
Do not carry private employer fork changes, private knowledge packs, internal
data, private prompts, or company deployment configuration between employers
unless that material is already public or the employer has given written
permission.

This document is project hygiene guidance, not legal advice. Review employment
agreements and company open-source policies before importing or contributing
work in an employment context.
