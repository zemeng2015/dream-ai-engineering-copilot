<!-- SPDX-License-Identifier: Apache-2.0 -->

# Open-Core Strategy

DREAM public core is the generic Apache-2.0 framework. It should stay reusable, synthetic-data only, and safe to publish.

Public core contains:

- Provider interfaces and default mock/local providers.
- Synthetic DemoCorp knowledge packs and example repositories.
- Deterministic workflows for requirements, PR review, eval, audit, codebase memory, and TestGen stubs.
- Config validation and plugin loading boundaries.

Private extensions contain:

- Private knowledge packs.
- Private LLM providers.
- Private prompt and redaction policies.
- Deployment config and artifact storage choices.
- Private connectors and operational glue.

The boundary is intentional: private extensions import DREAM core, but private code and generated artifacts should not be pushed back into the public repository. Generic improvements should be recreated with synthetic examples before upstreaming.
