# SPDX-License-Identifier: Apache-2.0

import hashlib
import hmac
import os
import time
from collections.abc import Mapping

from dream.core.errors import AccessDeniedError, ProviderConfigurationError
from dream.security.models import AccessContext, RequestPrincipal

PRINCIPAL_HEADER = "x-dream-principal-id"
TEAMS_HEADER = "x-dream-team-ids"
GROUPS_HEADER = "x-dream-group-ids"
ROLES_HEADER = "x-dream-roles"
TIMESTAMP_HEADER = "x-dream-identity-timestamp"
SIGNATURE_HEADER = "x-dream-identity-signature"
KEY_ID_HEADER = "x-dream-identity-key-id"
REQUEST_ID_HEADER = "x-request-id"


class SignedProxyIdentityProvider:
    """Verify identity headers signed by an approved authentication proxy.

    The API never trusts plain client-supplied identity headers. Private mode
    requires an HMAC secret supplied by the deployment secret manager, a short
    replay window, and an optional key id for rotation.
    """

    def __init__(
        self,
        *,
        secret: str,
        max_clock_skew_seconds: int = 60,
        key_id: str | None = None,
    ) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ProviderConfigurationError(
                "DREAM identity header secret must contain at least 32 bytes."
            )
        if not 10 <= max_clock_skew_seconds <= 300:
            raise ProviderConfigurationError(
                "DREAM identity clock skew must be between 10 and 300 seconds."
            )
        self._secret = secret.encode("utf-8")
        self.max_clock_skew_seconds = max_clock_skew_seconds
        self.key_id = key_id.strip() if key_id and key_id.strip() else None

    @classmethod
    def from_environment(cls) -> "SignedProxyIdentityProvider":
        secret = os.getenv("DREAM_IDENTITY_HEADER_SECRET", "")
        if not secret:
            raise ProviderConfigurationError(
                "Private mode requires DREAM_IDENTITY_HEADER_SECRET from an approved "
                "secret manager."
            )
        raw_skew = os.getenv("DREAM_IDENTITY_MAX_CLOCK_SKEW_SECONDS", "60")
        try:
            max_clock_skew_seconds = int(raw_skew)
        except ValueError as exc:
            raise ProviderConfigurationError(
                "DREAM_IDENTITY_MAX_CLOCK_SKEW_SECONDS must be an integer."
            ) from exc
        return cls(
            secret=secret,
            max_clock_skew_seconds=max_clock_skew_seconds,
            key_id=os.getenv("DREAM_IDENTITY_HEADER_KEY_ID"),
        )

    def authenticate(
        self,
        headers: Mapping[str, str],
        *,
        method: str,
        path: str,
        now: int | None = None,
    ) -> AccessContext:
        principal_id = self._required(headers, PRINCIPAL_HEADER)
        team_ids = self._subjects(self._required(headers, TEAMS_HEADER))
        group_ids = self._subjects(headers.get(GROUPS_HEADER, ""))
        roles = self._subjects(self._required(headers, ROLES_HEADER))
        request_id = self._required(headers, REQUEST_ID_HEADER)
        timestamp_value = self._required(headers, TIMESTAMP_HEADER)
        signature = self._required(headers, SIGNATURE_HEADER).lower()

        if "*" in team_ids:
            raise AccessDeniedError("Wildcard team access is forbidden in private mode.")
        try:
            timestamp = int(timestamp_value)
        except ValueError as exc:
            raise AccessDeniedError("Identity timestamp is invalid.") from exc
        current_time = int(time.time()) if now is None else now
        if abs(current_time - timestamp) > self.max_clock_skew_seconds:
            raise AccessDeniedError("Identity assertion is outside the replay window.")

        if self.key_id is not None and headers.get(KEY_ID_HEADER, "") != self.key_id:
            raise AccessDeniedError("Identity signing key id is invalid.")

        expected = self.signature_for(
            secret=self._secret,
            principal_id=principal_id,
            team_ids=team_ids,
            group_ids=group_ids,
            roles=roles,
            timestamp=timestamp,
            request_id=request_id,
            method=method,
            path=path,
        )
        if not hmac.compare_digest(signature, expected):
            raise AccessDeniedError("Identity signature is invalid.")

        return AccessContext(
            mode="private-extension",
            principal=RequestPrincipal(
                principal_id=principal_id,
                authenticated=True,
                team_ids=team_ids,
                group_ids=group_ids,
                roles=roles,
            ),
            request_id=request_id,
        )

    @classmethod
    def signature_for(
        cls,
        *,
        secret: str | bytes,
        principal_id: str,
        team_ids: set[str],
        group_ids: set[str],
        roles: set[str],
        timestamp: int,
        request_id: str,
        method: str,
        path: str,
    ) -> str:
        key = secret.encode("utf-8") if isinstance(secret, str) else secret
        payload = cls._canonical_payload(
            principal_id=principal_id,
            team_ids=team_ids,
            group_ids=group_ids,
            roles=roles,
            timestamp=timestamp,
            request_id=request_id,
            method=method,
            path=path,
        )
        return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _canonical_payload(
        *,
        principal_id: str,
        team_ids: set[str],
        group_ids: set[str],
        roles: set[str],
        timestamp: int,
        request_id: str,
        method: str,
        path: str,
    ) -> str:
        return "\n".join(
            [
                principal_id,
                ",".join(sorted(team_ids)),
                ",".join(sorted(group_ids)),
                ",".join(sorted(roles)),
                str(timestamp),
                request_id,
                method.upper(),
                path,
            ]
        )

    @staticmethod
    def _required(headers: Mapping[str, str], name: str) -> str:
        value = headers.get(name, "").strip()
        if not value:
            raise AccessDeniedError(f"Required identity header is missing: {name}.")
        return value

    @staticmethod
    def _subjects(value: str) -> set[str]:
        return {item.strip() for item in value.split(",") if item.strip()}
