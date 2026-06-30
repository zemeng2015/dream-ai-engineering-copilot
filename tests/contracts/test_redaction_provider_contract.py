# SPDX-License-Identifier: Apache-2.0

from dream.extensions import DefaultRedactionProvider


def test_default_redaction_provider_contract_redacts_secret_like_strings() -> None:
    provider = DefaultRedactionProvider()

    redacted = provider.redact("normal text api_key=super-secret-value token:abc123")

    assert "super-secret-value" not in redacted
    assert "abc123" not in redacted
    assert "[REDACTED]" in redacted


def test_default_redaction_provider_contract_keeps_normal_text() -> None:
    provider = DefaultRedactionProvider()
    text = "This is normal engineering text with no sensitive assignment."

    assert provider.redact(text) == text
