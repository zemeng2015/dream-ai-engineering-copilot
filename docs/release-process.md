<!-- SPDX-License-Identifier: Apache-2.0 -->

# Release Process

Recommended public core release flow:

1. Update `VERSION`, `CHANGELOG.md`, and package metadata.
2. Run `pytest` and `ruff check .`.
3. Run `dream demo verify`.
4. Tag the release in git.
5. Publish or distribute the tagged package.

Private extension repositories should pin a released public core version. Avoid depending directly on the public `main` branch because interfaces may move before a release tag.
