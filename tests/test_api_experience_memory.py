# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from dream.api.app import create_app


def test_experience_api_runs_three_session_memory_loop(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DREAM_EXPERIENCE_DB_PATH", str(tmp_path / "experience.sqlite"))
    client = TestClient(create_app())

    first = client.post(
        "/experience/capture",
        json={
            "team_id": "demo_team",
            "user_id": "zack",
            "session_id": "session-1",
            "observation": "preference:production_retry_mode=retry all tasks",
            "llm_provider": "deterministic",
        },
    )
    second = client.post(
        "/experience/capture",
        json={
            "team_id": "demo_team",
            "user_id": "zack",
            "session_id": "session-2",
            "observation": "preference:production_retry_mode=retry only failed tasks",
            "llm_provider": "deterministic",
        },
    )
    recall = client.post(
        "/experience/recall",
        json={
            "team_id": "demo_team",
            "user_id": "zack",
            "session_id": "session-3",
            "query": "What is the production retry mode?",
            "token_budget": 128,
        },
    )
    memories = client.get(
        "/experience/memories",
        params={
            "team_id": "demo_team",
            "user_id": "zack",
            "include_inactive": True,
        },
    )
    decisions = client.get(
        "/experience/decisions",
        params={"team_id": "demo_team", "user_id": "zack"},
    )

    assert first.status_code == 200
    assert first.json()["decision"]["action"] == "remember"
    assert second.status_code == 200
    assert second.json()["decision"]["action"] == "supersede"
    assert recall.status_code == 200
    assert recall.json()["selected"][0]["memory"]["value"] == "retry only failed tasks"
    assert "retry all tasks" not in recall.json()["context_card"]
    assert {item["status"] for item in memories.json()} == {"active", "superseded"}
    assert [item["action"] for item in decisions.json()] == ["remember", "supersede"]


def test_experience_feedback_api_updates_reusable_memory(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DREAM_EXPERIENCE_DB_PATH", str(tmp_path / "experience.sqlite"))
    client = TestClient(create_app())
    captured = client.post(
        "/experience/capture",
        json={
            "team_id": "demo_team",
            "user_id": "zack",
            "session_id": "session-1",
            "observation": "policy:production_retry_safety=ask for approval",
            "llm_provider": "deterministic",
        },
    ).json()

    response = client.post(
        "/experience/feedback",
        json={
            "team_id": "demo_team",
            "user_id": "zack",
            "memory_id": captured["memory"]["memory_id"],
            "helpful": True,
            "correct": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["feedback_count"] == 1
    assert response.json()["helpful_total"] == 1
    assert response.json()["correctness_total"] == 1

