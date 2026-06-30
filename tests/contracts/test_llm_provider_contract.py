# SPDX-License-Identifier: Apache-2.0

from dream.llm import LLMRequest, MockLLMProvider


def test_mock_llm_provider_contract_accepts_request_model() -> None:
    provider = MockLLMProvider()

    response = provider.complete(
        LLMRequest(prompt="Summarize this safely. api_key=super-secret-value")
    )

    assert response.text
    assert response.model_name
    assert response.provider_name == provider.provider_name
    assert isinstance(response.token_usage, dict)
    assert "super-secret-value" not in response.text
