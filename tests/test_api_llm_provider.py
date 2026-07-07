# SPDX-License-Identifier: Apache-2.0

import json

from fastapi.testclient import TestClient

from dream.api.app import create_app


class FakeOpenAIResponse:
    def __enter__(self) -> "FakeOpenAIResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "model": "demo-openai-model",
                "choices": [{"message": {"content": "# OpenAI API Draft\n\nDREAM_OK"}}],
            }
        ).encode("utf-8")


def test_requirement_draft_endpoint_accepts_openai_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "dream.llm.openai_compatible.urlopen",
        lambda request, timeout: FakeOpenAIResponse(),  # noqa: ARG005
    )
    client = TestClient(create_app())

    response = client.post(
        "/requirements/draft",
        json={
            "team_id": "demo_team",
            "rough_business_request": "Add async status tracking",
            "app": "ForecastDemo",
            "component": "job-execution",
            "llm_provider": "openai-compatible",
        },
    )

    assert response.status_code == 200
    assert response.json()["markdown"].startswith("# OpenAI API Draft")


def test_requirement_draft_endpoint_accepts_qwen_cloud_provider(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-qwen-key")
    monkeypatch.setattr(
        "dream.llm.openai_compatible.urlopen",
        lambda request, timeout: FakeOpenAIResponse(),  # noqa: ARG005
    )
    client = TestClient(create_app())

    response = client.post(
        "/requirements/draft",
        json={
            "team_id": "demo_team",
            "rough_business_request": "Add async status tracking",
            "app": "ForecastDemo",
            "component": "job-execution",
            "llm_provider": "qwen-cloud",
        },
    )

    assert response.status_code == 200
    assert response.json()["markdown"].startswith("# OpenAI API Draft")
