# PrivateDemo DREAM Extension Template

This template shows how to keep DREAM public core generic while a private repository supplies enterprise-specific behavior.

Recommended use:

1. Copy this folder into a private repository.
2. Copy `config/provider-approval.example.json` to an approved location outside
   the public checkout and replace every placeholder with the reviewed exact
   provider, endpoint, model, approver, and validity window.
3. Keep private knowledge packs under `knowledge_packs/`.
4. Set `DREAM_CONFIG_FILE` to `config/dream.private.example.yaml` or your private copy.
5. Set `DREAM_ARTIFACT_ROOT` to a path outside the public DREAM checkout.
6. Set `PILOT_OPENAI_API_KEY` through the approved secret manager and set
   `DREAM_LLM_APPROVAL_FILE` to the absolute approval-manifest path.
7. Pin the public DREAM core version in this package's dependency list.

The sample provider classes are deterministic contract examples; the private
runtime intentionally rejects LLM plugins until an attested plugin-egress
contract exists. The active template uses the built-in OpenAI-compatible
provider with exact approval enforcement.

Run contract checks from the public core against private providers before enabling them in shared environments.
