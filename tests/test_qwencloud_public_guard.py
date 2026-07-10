# SPDX-License-Identifier: Apache-2.0

import pytest
from fastapi import HTTPException

from dream.api import routes


def test_public_qwen_rate_limit_blocks_excess_requests(monkeypatch) -> None:
    monkeypatch.setenv("DREAM_PUBLIC_QWEN_REQUESTS_PER_MINUTE", "2")
    routes._PUBLIC_QWEN_REQUEST_TIMES.clear()

    routes._enforce_public_qwen_rate_limit()
    routes._enforce_public_qwen_rate_limit()

    with pytest.raises(HTTPException) as exc_info:
        routes._enforce_public_qwen_rate_limit()

    assert exc_info.value.status_code == 429
    routes._PUBLIC_QWEN_REQUEST_TIMES.clear()


def test_public_qwen_rate_limit_rejects_invalid_configuration(monkeypatch) -> None:
    monkeypatch.setenv("DREAM_PUBLIC_QWEN_REQUESTS_PER_MINUTE", "0")
    routes._PUBLIC_QWEN_REQUEST_TIMES.clear()

    with pytest.raises(HTTPException) as exc_info:
        routes._enforce_public_qwen_rate_limit()

    assert exc_info.value.status_code == 503


@pytest.mark.parametrize(
    ("selector", "resolve_provider"),
    [
        ("config", routes._llm_provider),
        ("plugin", routes._optional_llm_provider),
    ],
)
def test_configured_provider_cannot_bypass_public_qwen_rate_limit(
    monkeypatch, selector, resolve_provider
) -> None:
    monkeypatch.setenv("DREAM_PUBLIC_QWEN_REQUESTS_PER_MINUTE", "1")
    routes._PUBLIC_QWEN_REQUEST_TIMES.clear()
    monkeypatch.setattr(routes, "build_llm_provider", routes.MockLLMProvider)

    resolve_provider(selector)

    with pytest.raises(HTTPException) as exc_info:
        resolve_provider(selector)

    assert exc_info.value.status_code == 429
    routes._PUBLIC_QWEN_REQUEST_TIMES.clear()
