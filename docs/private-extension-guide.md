<!-- SPDX-License-Identifier: Apache-2.0 -->

# Private Extension Guide

Use `examples/private-extension-template/` as the starting point for a private DREAM extension repository.

Recommended setup:

1. Copy the template into a private repository.
2. Pin the public DREAM package version.
3. Implement provider classes under `private_plugins/`.
4. Place private knowledge packs under that private repository.
5. Set `DREAM_CONFIG_FILE` to the private config file.
6. Set `DREAM_ARTIFACT_ROOT` outside the public DREAM checkout.
7. Run `dream config validate`, `dream config doctor`, and provider contract tests.

The public repository should receive only generic interface or framework improvements. If a private workflow reveals a reusable enhancement, rebuild it with DemoCorp-style synthetic examples before contributing it to public core.
