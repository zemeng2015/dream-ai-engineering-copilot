<!-- SPDX-License-Identifier: Apache-2.0 -->

# Company Import Workflow

This workflow keeps private work outside the public DREAM repository.

1. Install or pin the public DREAM core package in a private environment.
2. Create a private extension repository from `examples/private-extension-template/`.
3. Add private knowledge packs and plugin implementations in the private repository.
4. Configure `DREAM_CONFIG_FILE` to point at the private config.
5. Configure `DREAM_ARTIFACT_ROOT` outside the public checkout.
6. Run `dream demo verify` against public synthetic data.
7. Run private smoke tests and provider contract tests in the private repository.

Do not import private names, private APIs, private prompts, or generated private artifacts into public core. Recreate reusable changes with synthetic fixtures before upstreaming.
