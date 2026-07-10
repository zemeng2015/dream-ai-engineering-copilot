# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_uses_same_origin_api_and_explicit_qwen_cloud_requests() -> None:
    service = (ROOT / "frontend/src/app/core/dream-api.service.ts").read_text(
        encoding="utf-8"
    )

    assert "resolveApiBaseUrl()" in service
    assert "window.location.origin" in service
    assert "llm_provider: 'qwen-cloud'" in service
    assert "llm_provider=qwen-cloud" in service
    assert "{ judge_provider: 'qwen-cloud' }" in service
    assert "llm_provider: 'openai-compatible'" not in service
    assert "llm_provider=openai-compatible" not in service
