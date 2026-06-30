# SPDX-License-Identifier: Apache-2.0

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from dream.api.app import create_app


def test_context_intelligence_and_retrieval_eval_api(tmp_path, monkeypatch) -> None:
    _configure_isolated_runtime(tmp_path, monkeypatch)
    client = TestClient(create_app())

    index_response = client.post(
        "/codebase/index",
        json={
            "team_id": "demo_team",
            "repo_path": "examples/dfp-demo-repo",
            "repo_name": "dfp-demo-repo",
        },
    )
    assert index_response.status_code == 200

    graph_response = client.post(
        "/graph/build",
        json={"team_id": "demo_team", "repo_name": "dfp-demo-repo"},
    )
    assert graph_response.status_code == 200

    create_response = client.post(
        "/requirement-cases",
        json={
            "team_id": "demo_team",
            "raw_request": (
                "Users want to know which task is still running when a forecast "
                "job takes too long"
            ),
            "created_by_role": "BA",
        },
    )
    assert create_response.status_code == 200
    case_id = create_response.json()["case"]["case_id"]

    analyze_response = client.post(f"/requirement-cases/{case_id}/analyze")
    assert analyze_response.status_code == 200

    trail_response = client.get(f"/context/trails/{case_id}")
    assert trail_response.status_code == 200
    assert trail_response.json()["selected_evidence"]

    pack_response = client.get(f"/context/packs/{case_id}")
    assert pack_response.status_code == 200
    assert pack_response.json()["selected_evidence_count"] > 0

    prompt_response = client.get(
        f"/context/prompt-preview/{case_id}",
        params={"target": "jira_draft"},
    )
    assert prompt_response.status_code == 200
    assert "Jira Story Draft" in prompt_response.json()["prompt_text"]

    eval_response = client.post(
        "/eval/retrieval",
        json={"case_id": case_id, "profile_id": "async-status-tracking"},
    )
    assert eval_response.status_code == 200
    assert eval_response.json()["scorecard"]["target_type"] == "retrieval_context"

    report_response = client.get(
        "/context/report",
        params={"team_id": "demo_team", "repo_name": "dfp-demo-repo"},
    )
    assert report_response.status_code == 200
    assert report_response.json()["top_concepts"]


def test_knowledge_intake_api_review_gate_and_promote(tmp_path, monkeypatch) -> None:
    _configure_isolated_runtime(tmp_path, monkeypatch)
    client = TestClient(create_app())

    upload_response = client.post(
        "/intake/documents",
        json={
            "team_id": "demo_team",
            "file_path": "examples/intake-samples/runbook-output-reconciliation.md",
            "document_type": "runbooks",
        },
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["document_id"]

    list_response = client.get("/intake/documents")
    assert list_response.status_code == 200
    assert any(item["document_id"] == document_id for item in list_response.json())

    parse_response = client.post(f"/intake/documents/{document_id}/parse")
    assert parse_response.status_code == 200
    draft_payload = parse_response.json()
    assert draft_payload["sections"]
    assert draft_payload["review_status"] == "pending_review"

    review_response = client.post(
        f"/intake/drafts/{draft_payload['draft_id']}/review",
        json={
            "status": "approved",
            "reviewer": "api-test",
            "notes": "Validated deterministic parsing for API test.",
        },
    )
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == "approved"

    promote_response = client.post(f"/intake/drafts/{draft_payload['draft_id']}/promote")
    assert promote_response.status_code == 200
    assert promote_response.json()["status"] == "promoted"


def _configure_isolated_runtime(tmp_path: Path, monkeypatch) -> None:
    knowledge_root = tmp_path / "knowledge_packs"
    shutil.copytree(Path("knowledge_packs"), knowledge_root)
    artifact_root = tmp_path / "artifacts"
    audit_path = tmp_path / "dream.sqlite"
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        f"""mode: public-demo
llm:
  provider: mock
knowledge:
  pack_root: "{knowledge_root.as_posix()}"
artifacts:
  root: "{artifact_root.as_posix()}"
audit:
  sqlite_path: "{audit_path.as_posix()}"
redaction:
  provider: default
prompt_policy:
  provider: default
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(audit_path))
