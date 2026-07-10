# SPDX-License-Identifier: Apache-2.0

import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from dream.api.app import create_app
from dream.security.identity import SignedProxyIdentityProvider

SECRET = "private-api-test-secret-with-at-least-thirty-two-bytes"


def _configure_private(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "dream-private.yaml"
    config_path.write_text("mode: private-extension\n", encoding="utf-8")
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("DREAM_IDENTITY_HEADER_SECRET", SECRET)


def _signed_headers(
    *,
    path: str,
    method: str = "GET",
    team_ids: set[str] | None = None,
    group_ids: set[str] | None = None,
    roles: set[str] | None = None,
) -> dict[str, str]:
    principal_id = "user-123"
    teams = team_ids or {"team-a"}
    groups = group_ids or {"engineering-a"}
    role_set = roles or {"viewer", "author"}
    timestamp = int(time.time())
    request_id = f"request-{uuid4().hex}"
    return {
        "x-dream-principal-id": principal_id,
        "x-dream-team-ids": ",".join(sorted(teams)),
        "x-dream-group-ids": ",".join(sorted(groups)),
        "x-dream-roles": ",".join(sorted(role_set)),
        "x-dream-identity-timestamp": str(timestamp),
        "x-request-id": request_id,
        "x-dream-identity-signature": SignedProxyIdentityProvider.signature_for(
            secret=SECRET,
            principal_id=principal_id,
            team_ids=teams,
            group_ids=groups,
            roles=role_set,
            timestamp=timestamp,
            request_id=request_id,
            method=method,
            path=path,
        ),
    }


def test_private_api_rejects_unsigned_and_unported_routes(monkeypatch, tmp_path: Path) -> None:
    _configure_private(monkeypatch, tmp_path)
    client = TestClient(create_app())

    unsigned = client.get("/requirement-cases")
    unported = client.get("/health", headers=_signed_headers(path="/health"))
    liveness = client.get("/health/live")
    openapi = client.get("/openapi.json")

    assert unsigned.status_code == 401
    assert unsigned.json()["detail"] == "Invalid authenticated identity assertion."
    assert unported.status_code == 503
    assert "disabled" in unported.json()["detail"]
    assert liveness.status_code == 200
    assert liveness.json() == {"status": "ok"}
    assert openapi.status_code == 404


def test_private_api_identity_signature_binds_query_string(monkeypatch, tmp_path: Path) -> None:
    _configure_private(monkeypatch, tmp_path)
    client = TestClient(create_app())
    signed_target = "/requirement-cases?team_id=team-a"
    headers = _signed_headers(path=signed_target)

    accepted = client.get(signed_target, headers=headers)
    tampered = client.get("/requirement-cases?team_id=team-b", headers=headers)

    assert accepted.status_code == 200
    assert tampered.status_code == 401


def test_private_requirement_case_is_acl_isolated(monkeypatch, tmp_path: Path) -> None:
    _configure_private(monkeypatch, tmp_path)
    client = TestClient(create_app())
    access = {
        "classification": "internal",
        "acl_scope": "source_acl",
        "allowed_group_ids": ["engineering-a"],
        "source_acl_version": "case-acl-v1",
    }

    created = client.post(
        "/requirement-cases",
        headers=_signed_headers(path="/requirement-cases", method="POST"),
        json={
            "team_id": "team-a",
            "raw_request": "Track long-running job status.",
            "access": access,
        },
    )
    assert created.status_code == 200
    case_id = created.json()["case"]["case_id"]

    owner_read = client.get(
        f"/requirement-cases/{case_id}",
        headers=_signed_headers(path=f"/requirement-cases/{case_id}"),
    )
    denied_read = client.get(
        f"/requirement-cases/{case_id}",
        headers=_signed_headers(
            path=f"/requirement-cases/{case_id}",
            group_ids={"other-group"},
        ),
    )
    cross_team_list = client.get(
        "/requirement-cases",
        headers=_signed_headers(path="/requirement-cases", team_ids={"team-b"}),
    )

    assert owner_read.status_code == 200
    assert owner_read.json()["case"]["access"]["source_acl_version"] == "case-acl-v1"
    assert denied_read.status_code == 404
    assert cross_team_list.status_code == 200
    assert cross_team_list.json() == []


def test_private_route_surface_is_explicitly_allowlisted() -> None:
    routes = {
        route.path: route.endpoint for route in create_app().routes if hasattr(route, "endpoint")
    }

    for path in [
        "/review/pr",
        "/codebase/search",
        "/graph/search",
        "/context/trails/{case_id}",
        "/memory/search",
        "/requirement-cases",
    ]:
        assert getattr(routes[path], "_dream_private_acl_enforced", False)

    for path in [
        "/codebase/index",
        "/graph/build",
        "/intake/documents",
        "/memory/scan",
        "/memory/review",
        "/audit/runs",
        "/eval/run",
    ]:
        assert not getattr(routes[path], "_dream_private_acl_enforced", False)

    assert getattr(routes["/health/live"], "_dream_private_anonymous_allowed", False)
