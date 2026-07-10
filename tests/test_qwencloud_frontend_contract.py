# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_uses_same_origin_api_and_profile_scoped_provider_policy() -> None:
    service = (ROOT / "frontend/src/app/core/dream-api.service.ts").read_text(
        encoding="utf-8"
    )
    profiles = (ROOT / "frontend/src/app/core/product-profile.ts").read_text(
        encoding="utf-8"
    )

    assert "resolveApiBaseUrl()" in service
    assert "window.location.origin" in service
    assert "llm_provider: this.productProfile.generationProvider" in service
    assert "llm_provider=${this.productProfile.generationProvider}" in service
    assert "judge_provider: this.productProfile.judgeProvider" in service
    assert "generationProvider: 'mock'" in profiles
    assert "judgeProvider: 'none'" in profiles
    assert "generationProvider: 'qwen-cloud'" in profiles
    assert "judgeProvider: 'qwen-cloud'" in profiles
    assert "llm_provider: 'openai-compatible'" not in service
    assert "llm_provider=openai-compatible" not in service
