<!-- SPDX-License-Identifier: Apache-2.0 -->

# Artifact Isolation

DREAM defaults to writing generated outputs under:

```text
artifacts/
```

Private extension usage should set:

```bash
export DREAM_ARTIFACT_ROOT=/path/to/private/dream-artifacts
```

All public workflows should resolve generated outputs through the configured artifact root. The local artifact store prevents path traversal, so paths like `../outside.md` are rejected.

In `private-extension` mode, `dream config validate` warns when the artifact root is inside the public repository. This warning is intentional: private generated outputs often contain private context and should stay in a private storage location.
