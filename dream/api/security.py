# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request

from dream.config import resolve_config
from dream.core.errors import AccessDeniedError, ProviderConfigurationError
from dream.security import AccessContext, SignedProxyIdentityProvider


def private_acl_route(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    """Mark an API route as explicitly wired to private ACL enforcement."""

    endpoint._dream_private_acl_enforced = True
    return endpoint


def private_anonymous_route(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    """Allow a deliberately data-free route before private authentication."""

    endpoint._dream_private_anonymous_allowed = True
    return endpoint


def identity_boundary(request: Request) -> None:
    """Authenticate private requests and fail closed on unported routes."""

    mode = resolve_config().mode
    if mode == "public-demo":
        request.state.access_context = AccessContext.public_demo()
        return

    endpoint = request.scope.get("endpoint")
    if endpoint is not None and getattr(
        endpoint,
        "_dream_private_anonymous_allowed",
        False,
    ):
        return

    try:
        raw_path = request.scope.get("raw_path", request.url.path.encode("utf-8"))
        query_string = request.scope.get("query_string", b"")
        request_target = raw_path.decode("latin-1")
        if query_string:
            request_target = f"{request_target}?{query_string.decode('latin-1')}"
        context = SignedProxyIdentityProvider.from_environment().authenticate(
            request.headers,
            method=request.method,
            path=request_target,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="Private identity boundary is not configured.",
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated identity assertion.",
        ) from exc

    if endpoint is None or not getattr(endpoint, "_dream_private_acl_enforced", False):
        raise HTTPException(
            status_code=503,
            detail="This route is disabled until private ACL enforcement is wired.",
        )
    request.state.access_context = context


def get_access_context(request: Request) -> AccessContext:
    context = getattr(request.state, "access_context", None)
    if context is None:
        identity_boundary(request)
        context = getattr(request.state, "access_context", None)
    if not isinstance(context, AccessContext):
        raise HTTPException(status_code=500, detail="Access context was not initialized.")
    return context
