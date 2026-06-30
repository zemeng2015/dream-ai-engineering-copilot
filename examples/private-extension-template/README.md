# PrivateDemo DREAM Extension Template

This template shows how to keep DREAM public core generic while a private repository supplies enterprise-specific behavior.

Recommended use:

1. Copy this folder into a private repository.
2. Implement private providers under `private_plugins/`.
3. Keep private knowledge packs under `knowledge_packs/`.
4. Set `DREAM_CONFIG_FILE` to `config/dream.private.example.yaml` or your private copy.
5. Set `DREAM_ARTIFACT_ROOT` to a path outside the public DREAM checkout.
6. Pin the public DREAM core version in this package's dependency list.

The sample providers are deterministic and do not call any real API. Replace them in the private repository only.

Run contract checks from the public core against private providers before enabling them in shared environments.
