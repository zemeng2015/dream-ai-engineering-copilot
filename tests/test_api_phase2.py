# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from dream.api.app import create_app


def test_codebase_index_and_search_endpoints() -> None:
    client = TestClient(create_app())

    index_response = client.post(
        "/codebase/index",
        json={
            "team_id": "demo_team",
            "repo_path": "examples/java-demo-repo",
            "repo_name": "java-demo-repo",
        },
    )
    assert index_response.status_code == 200
    assert index_response.json()["repo_name"] == "java-demo-repo"

    search_response = client.get(
        "/codebase/search",
        params={
            "team_id": "demo_team",
            "repo_name": "java-demo-repo",
            "query": "async status tracking",
        },
    )
    assert search_response.status_code == 200
    assert any("AsyncJobStatusTracker" in item["title"] for item in search_response.json())


def test_requirement_case_endpoints() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/requirement-cases",
        json={
            "team_id": "demo_team",
            "raw_request": "Add async status tracking for long-running job execution",
            "created_by_role": "BA",
        },
    )
    assert create_response.status_code == 200
    case_id = create_response.json()["case"]["case_id"]

    analyze_response = client.post(f"/requirement-cases/{case_id}/analyze")
    assert analyze_response.status_code == 200
    assert analyze_response.json()["impact_items"]

    brief_response = client.get(f"/requirement-cases/{case_id}/brief")
    assert brief_response.status_code == 200
    assert "# Engineering Brief" in brief_response.json()["markdown"]
