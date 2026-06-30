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


def test_evidence_graph_endpoints() -> None:
    client = TestClient(create_app())
    client.post(
        "/codebase/index",
        json={
            "team_id": "demo_team",
            "repo_path": "examples/dfp-demo-repo",
            "repo_name": "dfp-demo-repo",
        },
    )

    build_response = client.post(
        "/graph/build",
        json={"team_id": "demo_team", "repo_name": "dfp-demo-repo"},
    )
    assert build_response.status_code == 200
    assert build_response.json()["edges"]

    search_response = client.get(
        "/graph/search",
        params={
            "team_id": "demo_team",
            "repo_name": "dfp-demo-repo",
            "query": "execution status",
        },
    )
    assert search_response.status_code == 200
    assert any("StatusTracker" in str(item) for item in search_response.json())


def test_memory_distillation_endpoints() -> None:
    client = TestClient(create_app())

    scan_response = client.post(
        "/memory/scan",
        json={
            "team_id": "demo_team",
            "repo_path": "examples/java-demo-repo",
            "repo_name": "java-demo-repo",
        },
    )
    assert scan_response.status_code == 200
    scan_payload = scan_response.json()
    assert scan_payload["schema_version"] == "memory-scan-v0.2"
    assert scan_payload["provenance"]["repo_path"] == "examples/java-demo-repo"
    assert scan_payload["claims"]
    candidate_claim = next(
        claim for claim in scan_payload["claims"] if claim["governance"]["status"] == "candidate"
    )

    diff_response = client.get("/memory/diff", params={"team_id": "demo_team"})
    assert diff_response.status_code == 200
    assert "# Memory Diff" in diff_response.json()["markdown"]

    review_response = client.post(
        "/memory/review",
        json={
            "team_id": "demo_team",
            "claim_id": candidate_claim["claim_id"],
            "status": "approved",
            "reviewer": "api-test",
            "reason": "Validated in API test.",
        },
    )
    assert review_response.status_code == 200
    assert review_response.json()["new_status"] == "approved"

    search_response = client.get(
        "/memory/search",
        params={
            "team_id": "demo_team",
            "query": candidate_claim["entity"]["canonical_name"],
        },
    )
    assert search_response.status_code == 200
    assert any(
        item["claim"]["claim_id"] == candidate_claim["claim_id"]
        for item in search_response.json()
    )

    context_response = client.get(
        "/memory/context-card",
        params={
            "team_id": "demo_team",
            "query": candidate_claim["entity"]["canonical_name"],
        },
    )
    assert context_response.status_code == 200
    assert "DREAM Memory Context Card" in context_response.json()["markdown"]

    eval_response = client.post("/memory/eval", json={"team_id": "demo_team"})
    assert eval_response.status_code == 200
    assert eval_response.json()["pass_status"] == "pass"
