# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.core.errors import AccessDeniedError, ProviderConfigurationError
from dream.security.identity import SignedProxyIdentityProvider

SECRET = "test-only-identity-secret-with-at-least-32-bytes"
NOW = 1_800_000_000


def _headers(
    *,
    method: str = "GET",
    path: str = "/requirement-cases",
    **overrides: str,
) -> dict[str, str]:
    headers = {
        "x-dream-principal-id": "user-123",
        "x-dream-team-ids": "team-a",
        "x-dream-group-ids": "engineering-a,qa-a",
        "x-dream-roles": "viewer,author",
        "x-dream-identity-timestamp": str(NOW),
        "x-request-id": "request-42",
    }
    headers.update(overrides)
    headers["x-dream-identity-signature"] = SignedProxyIdentityProvider.signature_for(
        secret=SECRET,
        principal_id=headers["x-dream-principal-id"],
        team_ids={item for item in headers["x-dream-team-ids"].split(",") if item},
        group_ids={item for item in headers["x-dream-group-ids"].split(",") if item},
        roles={item for item in headers["x-dream-roles"].split(",") if item},
        timestamp=int(headers["x-dream-identity-timestamp"]),
        request_id=headers["x-request-id"],
        method=method,
        path=path,
    )
    return headers


def test_signed_proxy_identity_authenticates_normalized_context() -> None:
    context = SignedProxyIdentityProvider(secret=SECRET).authenticate(
        _headers(),
        method="GET",
        path="/requirement-cases",
        now=NOW,
    )

    assert context.mode == "private-extension"
    assert context.principal.authenticated
    assert context.principal.principal_id == "user-123"
    assert context.principal.team_ids == {"team-a"}
    assert context.principal.group_ids == {"engineering-a", "qa-a"}
    assert context.principal.roles == {"viewer", "author"}
    assert context.request_id == "request-42"


def test_signed_proxy_identity_rejects_tampering_and_expired_assertions() -> None:
    tampered = _headers()
    tampered["x-dream-team-ids"] = "team-b"

    with pytest.raises(AccessDeniedError, match="signature"):
        SignedProxyIdentityProvider(secret=SECRET).authenticate(
            tampered,
            method="GET",
            path="/requirement-cases",
            now=NOW,
        )
    with pytest.raises(AccessDeniedError, match="replay window"):
        SignedProxyIdentityProvider(secret=SECRET).authenticate(
            _headers(),
            method="GET",
            path="/requirement-cases",
            now=NOW + 61,
        )


def test_signed_proxy_identity_rejects_wildcard_team_and_wrong_key_id() -> None:
    with pytest.raises(AccessDeniedError, match="Wildcard"):
        SignedProxyIdentityProvider(secret=SECRET).authenticate(
            _headers(**{"x-dream-team-ids": "*"}),
            method="GET",
            path="/requirement-cases",
            now=NOW,
        )

    with pytest.raises(AccessDeniedError, match="key id"):
        SignedProxyIdentityProvider(secret=SECRET, key_id="key-2").authenticate(
            _headers(**{"x-dream-identity-key-id": "key-1"}),
            method="GET",
            path="/requirement-cases",
            now=NOW,
        )


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ("x-dream-team-ids", "team membership"),
        ("x-dream-roles", "at least one role"),
    ],
)
def test_signed_proxy_identity_rejects_empty_subject_sets(
    header: str,
    message: str,
) -> None:
    with pytest.raises(AccessDeniedError, match=message):
        SignedProxyIdentityProvider(secret=SECRET).authenticate(
            _headers(**{header: ",,,"}),
            method="GET",
            path="/requirement-cases",
            now=NOW,
        )


def test_signed_proxy_identity_is_bound_to_method_and_path() -> None:
    headers = _headers(method="GET", path="/requirement-cases")
    provider = SignedProxyIdentityProvider(secret=SECRET)

    with pytest.raises(AccessDeniedError, match="signature"):
        provider.authenticate(
            headers,
            method="POST",
            path="/requirement-cases",
            now=NOW,
        )
    with pytest.raises(AccessDeniedError, match="signature"):
        provider.authenticate(
            headers,
            method="GET",
            path="/audit/runs",
            now=NOW,
        )


def test_signed_proxy_identity_is_bound_to_query_string() -> None:
    headers = _headers(path="/codebase/search?team_id=team-a&query=status")
    provider = SignedProxyIdentityProvider(secret=SECRET)

    provider.authenticate(
        headers,
        method="GET",
        path="/codebase/search?team_id=team-a&query=status",
        now=NOW,
    )
    with pytest.raises(AccessDeniedError, match="signature"):
        provider.authenticate(
            headers,
            method="GET",
            path="/codebase/search?team_id=team-a&query=payroll",
            now=NOW,
        )


def test_signed_proxy_identity_configuration_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_IDENTITY_HEADER_SECRET", raising=False)
    with pytest.raises(ProviderConfigurationError, match="requires"):
        SignedProxyIdentityProvider.from_environment()

    with pytest.raises(ProviderConfigurationError, match="32 bytes"):
        SignedProxyIdentityProvider(secret="too-short")
