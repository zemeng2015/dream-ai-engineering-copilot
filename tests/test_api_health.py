# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from dream.api.app import create_app


def test_api_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

