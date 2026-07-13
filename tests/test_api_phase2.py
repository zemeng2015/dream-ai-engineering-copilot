# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from dream.api.app import create_app
from dream.memory.repository import MemoryDistillationRepository


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

    artifact_response = client.get(
        "/codebase/index",
        params={"team_id": "demo_team", "repo_name": "java-demo-repo"},
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json()["index"]["repo_name"] == "java-demo-repo"
    assert artifact_response.json()["index_path"].endswith("java-demo-repo.json")

    file_response = client.get(
        "/codebase/file-content",
        params={
            "team_id": "demo_team",
            "repo_name": "java-demo-repo",
            "file_path": "src/main/java/com/democorp/demo/AsyncJobStatusTracker.java",
        },
    )
    assert file_response.status_code == 200
    assert "class AsyncJobStatusTracker" in file_response.json()["content"]


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


def test_pr_review_accepts_inline_diff_and_jira_context() -> None:
    client = TestClient(create_app())
    diff_text = """diff --git a/src/OutputCollector.java b/src/OutputCollector.java
--- a/src/OutputCollector.java
+++ b/src/OutputCollector.java
@@ -1 +1,2 @@
-old output status
+new output reconciliation status
+retry needed when skipped files remain
"""

    response = client.post(
        "/review/pr",
        json={
            "team_id": "demo_team",
            "pr_diff_text": diff_text,
            "jira_context_text": "Jira asks for output reconciliation retry behavior.",
            "repo_name": "dfp-demo-repo",
            "app": "ForecastDemo",
            "component": "output-collection",
        },
    )

    assert response.status_code == 200
    assert response.json()["run_id"].startswith("pr-")
    assert "# AI PR Review Summary" in response.json()["markdown"]

    rating_response = client.post(
        f"/audit/runs/{response.json()['run_id']}/ratings",
        json={
            "usefulness_score": 4,
            "correctness_score": 3,
            "comments": "Useful API-backed review, needs final human validation.",
        },
    )
    assert rating_response.status_code == 200
    assert rating_response.json()["run_id"] == response.json()["run_id"]
    assert rating_response.json()["usefulness_score"] == 4

    ratings_response = client.get(f"/audit/runs/{response.json()['run_id']}/ratings")
    assert ratings_response.status_code == 200
    assert any(
        rating["comments"] == "Useful API-backed review, needs final human validation."
        for rating in ratings_response.json()
    )


def test_pr_review_rejects_missing_diff_input() -> None:
    client = TestClient(create_app())

    response = client.post("/review/pr", json={"team_id": "demo_team"})

    assert response.status_code == 400
    assert "pr_diff_text or pr_diff_path" in response.json()["detail"]


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
    assert scan_payload["schema_version"] == "memory-scan-v0.3"
    assert scan_payload["provenance"]["repo_path"] == "examples/java-demo-repo"
    assert scan_payload["claims"]
    candidate_claim = next(
        claim
        for claim in scan_payload["claims"]
        if claim["governance"]["status"] == "candidate"
        and claim["extraction"]["method"] == "heuristic_semantic"
    )
    claim_source_path = candidate_claim["evidence"]["spans"][0]["path"]
    source_response = client.get(
        f"/memory/claims/{candidate_claim['claim_id']}/source",
        params={
            "team_id": "demo_team",
            "scan_id": scan_payload["scan_id"],
            "source_path": claim_source_path,
        },
    )
    assert source_response.status_code == 200
    source_payload = source_response.json()
    assert source_payload["claim_id"] == candidate_claim["claim_id"]
    assert source_payload["source_path"] == claim_source_path
    assert source_payload["content"]
    assert source_payload["spans"]

    unrelated_source_response = client.get(
        f"/memory/claims/{candidate_claim['claim_id']}/source",
        params={
            "team_id": "demo_team",
            "scan_id": scan_payload["scan_id"],
            "source_path": "README.md",
        },
    )
    assert unrelated_source_response.status_code == 404

    diff_response = client.get("/memory/diff", params={"team_id": "demo_team"})
    assert diff_response.status_code == 200
    assert "# Memory Diff" in diff_response.json()["markdown"]

    repository = MemoryDistillationRepository()
    scan_model = repository.load_scan("demo_team", scan_payload["scan_id"])
    candidate_model = next(
        claim
        for claim in scan_model.claims
        if claim.claim_id == candidate_claim["claim_id"]
    )
    candidate_model = candidate_model.model_copy(
        deep=True,
        update={
            "relation": candidate_model.relation.model_copy(
                update={"type": "current_policy", "value": "api-source-policy"}
            ),
        },
    )
    conflicting_model = candidate_model.model_copy(
        deep=True,
        update={
            "claim_id": f"{candidate_model.claim_id}:api-conflict:{scan_payload['scan_id']}",
            "relation": candidate_model.relation.model_copy(
                update={"value": "api-conflicting-policy"}
            ),
        },
    )
    repository.save_scan(
        scan_model.model_copy(
            update={
                "claims": [
                    *[
                        claim
                        if claim.claim_id != candidate_model.claim_id
                        else candidate_model
                        for claim in scan_model.claims
                    ],
                    conflicting_model,
                ]
            }
        )
    )

    conflicts_response = client.get(
        "/memory/conflicts",
        params={"team_id": "demo_team", "scan_id": scan_payload["scan_id"]},
    )
    assert conflicts_response.status_code == 200
    conflicts_payload = conflicts_response.json()
    assert conflicts_payload["scan_id"] == scan_payload["scan_id"]
    assert conflicts_payload["conflict_count"] == 1
    assert isinstance(conflicts_payload["pairs"], list)

    resolve_response = client.post(
        "/memory/conflicts/resolve",
        json={
            "team_id": "demo_team",
            "scan_id": scan_payload["scan_id"],
            "conflict_id": conflicts_payload["pairs"][0]["conflict_id"],
            "winning_claim_id": candidate_model.claim_id,
            "reviewer": "api-test",
            "reason": "API test resolved conflict.",
        },
    )
    assert resolve_response.status_code == 200
    resolve_payload = resolve_response.json()
    assert resolve_payload["action"] == "approve_winner_reject_other"
    assert resolve_payload["winning_claim_id"] == candidate_model.claim_id
    assert resolve_payload["rejected_claim_id"] == conflicting_model.claim_id
    assert len(resolve_payload["review_event_ids"]) == 2

    resolutions_response = client.get(
        "/memory/conflict-resolutions",
        params={"team_id": "demo_team"},
    )
    assert resolutions_response.status_code == 200
    assert any(
        event["event_id"] == resolve_payload["event_id"]
        for event in resolutions_response.json()["events"]
    )

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
    review_payload = review_response.json()
    assert review_payload["new_status"] == "approved"
    assert review_payload["signal_explanations"]
    assert any(
        item["signal"] == "semantic_claim_requires_human_review"
        and item["severity"] == "warning"
        for item in review_payload["signal_explanations"]
    )

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
