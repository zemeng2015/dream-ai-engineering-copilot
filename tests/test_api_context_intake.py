# SPDX-License-Identifier: Apache-2.0

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from dream.api.app import create_app
from dream.audit.logger import AuditLogger


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
    question_ids = [item["question_id"] for item in analyze_response.json()["questions"]]
    assert question_ids

    not_ready_response = client.get(f"/requirement-cases/{case_id}/jira-readiness")
    assert not_ready_response.status_code == 200
    assert not_ready_response.json()["ready"] is False

    waived_question_id = question_ids[0]
    waive_response = client.post(
        f"/requirement-cases/{case_id}/questions/{waived_question_id}/waive",
        json={
            "reason": "Already covered by accepted criteria for this API test.",
            "waived_by": "api-test",
        },
    )
    assert waive_response.status_code == 200
    assert waive_response.json()["status"] == "waived"
    assert waive_response.json()["waived_reason"].startswith("Already covered")

    for question_id in question_ids[1:]:
        answer_response = client.post(
            f"/requirement-cases/{case_id}/questions/{question_id}/answer",
            json={
                "answer": f"API answer for {question_id}.",
                "answered_by": "api-test",
            },
        )
        assert answer_response.status_code == 200
        assert answer_response.json()["status"] == "answered"

    trail_response = client.get(f"/context/trails/{case_id}")
    assert trail_response.status_code == 200
    assert trail_response.json()["selected_evidence"]

    pack_response = client.get(f"/context/packs/{case_id}")
    assert pack_response.status_code == 200
    assert pack_response.json()["selected_evidence_count"] > 0

    jira_response = client.get(f"/requirement-cases/{case_id}/jira-draft")
    assert jira_response.status_code == 200
    assert "API answer for" in jira_response.json()["markdown"]
    assert "Waived: Already covered by accepted criteria" in jira_response.json()["markdown"]

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

    ready_response = client.get(f"/requirement-cases/{case_id}/jira-readiness")
    assert ready_response.status_code == 200
    assert ready_response.json()["ready"] is True
    assert ready_response.json()["waived_questions"] == 1

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
    assert upload_response.json()["source_hash"].startswith("sha256:")

    list_response = client.get("/intake/documents")
    assert list_response.status_code == 200
    assert any(item["document_id"] == document_id for item in list_response.json())

    parse_response = client.post(f"/intake/documents/{document_id}/parse")
    assert parse_response.status_code == 200
    draft_payload = parse_response.json()
    assert draft_payload["sections"]
    assert draft_payload["source_hash"] == upload_response.json()["source_hash"]
    assert all(
        section["section_hash"].startswith("sha256:")
        for section in draft_payload["sections"]
    )
    assert all(section["source_span"] for section in draft_payload["sections"])
    assert draft_payload["review_status"] == "pending_review"

    metadata_response = client.patch(
        f"/intake/drafts/{draft_payload['draft_id']}/metadata",
        json={
            "title": "Reviewed Output Reconciliation Test Plan",
            "target_doc_type": "testing",
            "app": "ForecastDemo",
            "component": "qa-automation",
            "concepts": ["output reconciliation", "retry coverage"],
            "reviewer": "api-test",
            "notes": "Metadata normalized during API test.",
        },
    )
    assert metadata_response.status_code == 200
    metadata_payload = metadata_response.json()
    assert metadata_payload["title"] == "Reviewed Output Reconciliation Test Plan"
    assert metadata_payload["target_doc_type"] == "testing"
    assert "component: qa-automation" in metadata_payload["normalized_markdown"]

    get_draft_response = client.get(f"/intake/drafts/{draft_payload['draft_id']}")
    assert get_draft_response.status_code == 200
    assert get_draft_response.json()["target_doc_type"] == "testing"
    assert get_draft_response.json()["sections"][0]["section_hash"].startswith("sha256:")

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
    assert "/docs/testing/" in promote_response.json()["promoted_path"]
    AuditLogger().log_generation(
        run_id="jira-draft-case-demo",
        use_case="jira_draft",
        team_id="demo_team",
        input_payload={"document_id": document_id},
        retrieved_source_paths=[promote_response.json()["promoted_path"]],
        model_provider="deterministic",
        model_name="requirement-case-jira-v1",
        output_path="artifacts/requirement-cases/case-demo/jira-draft.md",
        status="success",
        warnings=[],
    )
    promoted_list_response = client.get("/intake/documents")
    promoted_document = next(
        item for item in promoted_list_response.json() if item["document_id"] == document_id
    )
    assert promoted_document["promoted_path"] == promote_response.json()["promoted_path"]

    detail_response = client.get(f"/intake/documents/{document_id}/detail")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["document"]["document_id"] == document_id
    assert detail_payload["draft"]["review_status"] == "promoted"
    assert detail_payload["raw_size_bytes"] > 0
    assert detail_payload["source_hash_verified"] is True
    assert "Output Reconciliation Runbook" in detail_payload["raw_text"]
    assert detail_payload["draft"]["sections"][0]["source_span"]
    assert detail_payload["draft"]["sections"][0]["section_hash"].startswith("sha256:")
    assert {event["event_type"] for event in detail_payload["review_events"]} == {
        "metadata_update",
        "review_decision",
        "promotion",
    }
    metadata_event = next(
        event
        for event in detail_payload["review_events"]
        if event["event_type"] == "metadata_update"
    )
    assert metadata_event["reviewer"] == "api-test"
    assert metadata_event["audit_run_id"] == f"intake-metadata-{draft_payload['draft_id']}"
    assert any(
        diff["field"] == "target_doc_type"
        and diff["before"] == "runbooks"
        and diff["after"] == "testing"
        for diff in metadata_event["metadata_diff"]
    )
    review_events_response = client.get(
        f"/intake/drafts/{draft_payload['draft_id']}/review-events"
    )
    assert review_events_response.status_code == 200
    assert review_events_response.json()[0]["event_type"] in {
        "promotion",
        "review_decision",
        "metadata_update",
    }
    assert any(
        event["use_case"] == "knowledge_intake_promote"
        for event in detail_payload["audit_events"]
    )
    assert any(
        event["use_case"] == "jira_draft"
        for event in detail_payload["downstream_events"]
    )
    assert detail_payload["downstream_usages"][0]["audit_record"]["use_case"] == "jira_draft"
    assert detail_payload["downstream_usages"][0]["matched_source_paths"] == [
        promote_response.json()["promoted_path"]
    ]
    assert (
        detail_payload["downstream_usages"][0]["match_reason"]
        == "Retrieved source matched promoted structured Markdown."
    )
    assert detail_payload["downstream_usages"][0]["detail_route"] == "/audit/jira-draft-case-demo"
    proof = detail_payload["downstream_usages"][0]["match_proofs"][0]
    assert proof["retrieved_source_path"] == promote_response.json()["promoted_path"]
    assert proof["matched_path"] == promote_response.json()["promoted_path"]
    assert proof["matched_label"] == "promoted structured Markdown"
    assert proof["document_id"] == document_id
    assert proof["draft_id"] == draft_payload["draft_id"]
    assert proof["source_hash"] == upload_response.json()["source_hash"]
    assert proof["source_hash_verified"] is True
    assert proof["section_proofs"][0]["source_span"]
    assert proof["section_proofs"][0]["section_hash"].startswith("sha256:")

    memory_scan_response = client.post(
        "/memory/scan",
        json={
            "team_id": "demo_team",
            "repo_path": "examples/java-demo-repo",
            "repo_name": "java-demo-repo",
        },
    )
    assert memory_scan_response.status_code == 200
    scan_payload = memory_scan_response.json()
    claims_with_intake_proofs = [
        claim for claim in scan_payload["claims"] if claim["evidence"]["intake_proofs"]
    ]
    assert claims_with_intake_proofs
    selected_claim = claims_with_intake_proofs[0]
    memory_proof = selected_claim["evidence"]["intake_proofs"][0]
    assert memory_proof["document_id"] == document_id
    assert memory_proof["draft_id"] == draft_payload["draft_id"]
    assert memory_proof["promoted_path"] == promote_response.json()["promoted_path"]
    assert memory_proof["source_hash"] == upload_response.json()["source_hash"]
    assert memory_proof["source_hash_verified"] is True
    assert memory_proof["review_status"] == "promoted"
    assert memory_proof["match_explanation"].startswith("Matched claim")
    assert "deterministic terms" in memory_proof["match_explanation"]
    assert memory_proof["matched_terms"]
    assert any(
        run_id.startswith("intake-promote-")
        for run_id in memory_proof["intake_audit_run_ids"]
    )
    assert memory_proof["section_proofs"][0]["section_hash"].startswith("sha256:")

    review_claim_response = client.post(
        "/memory/review",
        json={
            "team_id": "demo_team",
            "claim_id": selected_claim["claim_id"],
            "status": "approved",
            "reviewer": "api-test",
            "reason": "Validated intake proof traceability.",
        },
    )
    assert review_claim_response.status_code == 200

    context_case_response = client.post(
        "/requirement-cases",
        json={
            "team_id": "demo_team",
            "raw_request": selected_claim["entity"]["canonical_name"],
            "created_by_role": "BA",
        },
    )
    assert context_case_response.status_code == 200
    context_trail_response = client.get(
        f"/context/trails/{context_case_response.json()['case']['case_id']}"
    )
    assert context_trail_response.status_code == 200
    used_claim = next(
        (
            claim
            for claim in context_trail_response.json()["memory_claims_used"]
            if any(proof["document_id"] == document_id for proof in claim["intake_proofs"])
        ),
        None,
    )
    assert used_claim is not None
    used_proof = next(
        proof for proof in used_claim["intake_proofs"] if proof["document_id"] == document_id
    )
    assert used_proof["draft_id"] == draft_payload["draft_id"]
    assert used_proof["match_explanation"].startswith("Matched claim")
    assert used_proof["matched_terms"]
    assert used_proof["section_proofs"][0]["section_hash"].startswith(
        "sha256:"
    )

    memory_diff_response = client.get(
        "/memory/diff",
        params={"team_id": "demo_team", "scan_id": scan_payload["scan_id"]},
    )
    assert memory_diff_response.status_code == 200
    assert f"intake proof: {document_id}" in memory_diff_response.json()["markdown"]
    assert "match explanation: Matched claim" in memory_diff_response.json()["markdown"]


def test_knowledge_intake_api_browser_upload(tmp_path, monkeypatch) -> None:
    _configure_isolated_runtime(tmp_path, monkeypatch)
    client = TestClient(create_app())

    upload_response = client.post(
        "/intake/documents/upload",
        data={"team_id": "demo_team", "document_type": "runbooks"},
        files={
            "file": (
                "browser-output-runbook.md",
                b"# Browser Output Runbook\n\n## Retry\nCheck execution status before retry.",
                "text/markdown",
            )
        },
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["original_path"] == "uploaded://browser-output-runbook.md"
    assert payload["source_hash"].startswith("sha256:")
    assert payload["status"] == "uploaded"

    parse_response = client.post(f"/intake/documents/{payload['document_id']}/parse")
    assert parse_response.status_code == 200
    assert parse_response.json()["sections"]


def test_pr_review_context_artifacts_are_available_through_context_api(
    tmp_path,
    monkeypatch,
) -> None:
    _configure_isolated_runtime(tmp_path, monkeypatch)
    client = TestClient(create_app())
    review_response = client.post(
        "/review/pr",
        json={
            "team_id": "demo_team",
            "repo_name": "dfp-demo-repo",
            "pr_diff_text": "\n".join(
                [
                    "diff --git a/status.ts b/status.ts",
                    "--- a/status.ts",
                    "+++ b/status.ts",
                    "@@ -1 +1,2 @@",
                    "-return status;",
                    "+return taskStatus;",
                ]
            ),
            "jira_context_text": "Show task-level execution status.",
            "llm_provider": "mock",
        },
    )
    assert review_response.status_code == 200
    payload = review_response.json()
    run_id = payload["run_id"]
    assert payload["context_trail_id"] == f"context-trail-{run_id}"

    trail_response = client.get(f"/context/trails/{run_id}")
    assert trail_response.status_code == 200
    assert trail_response.json()["run_id"] == run_id
    assert trail_response.json()["review_id"] == run_id

    pack_response = client.get(f"/context/packs/{run_id}")
    assert pack_response.status_code == 200
    assert pack_response.json()["run_id"] == run_id

    preview_response = client.get(f"/context/prompt-preview/{run_id}")
    assert preview_response.status_code == 200
    assert preview_response.json()["run_id"] == run_id
    assert preview_response.json()["target"] == "pr_review"


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
