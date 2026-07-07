# SPDX-License-Identifier: Apache-2.0

"""Verify raw document intake to traceable structured memory.

This script runs the public-demo raw-doc acceptance path through FastAPI routes:
upload/register, parse, metadata edit, review, promote, downstream retrieval,
memory scan, claim review, context trace, and audit/detail lookups.

By default it uses an isolated temporary artifact root, knowledge-pack copy, and
SQLite audit database so the local repo state is not mutated.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = "examples/intake-samples/runbook-output-reconciliation.md"


class AcceptanceError(RuntimeError):
    """Raised when an acceptance checkpoint fails."""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify DREAM raw doc -> structured memory traceability."
    )
    parser.add_argument("--team", default="demo_team")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--repo-path", default="examples/java-demo-repo")
    parser.add_argument("--repo-name", default="java-demo-repo")
    parser.add_argument("--title", default="Reviewed Output Reconciliation Test Plan")
    parser.add_argument("--target-doc-type", default="testing")
    parser.add_argument("--app", default="ForecastDemo")
    parser.add_argument("--component", default="qa-automation")
    parser.add_argument(
        "--query",
        default="output reconciliation retry coverage qa automation",
        help="Query used for downstream requirement draft and memory context checks.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory where isolated acceptance artifacts are created and preserved.",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep the temporary acceptance directory for inspection.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    run_dir, should_cleanup = _prepare_run_dir(args.work_dir, args.keep_artifacts)
    try:
        result = run_flow(args, run_dir)
    except Exception as exc:  # noqa: BLE001 - acceptance script should print concise failure.
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "run_dir": run_dir.as_posix(),
                    },
                    indent=2,
                )
            )
        else:
            print(f"FAIL raw-doc-memory-flow: {exc}", file=sys.stderr)
            print(f"run_dir: {run_dir}", file=sys.stderr)
        return 1
    finally:
        if should_cleanup:
            shutil.rmtree(run_dir, ignore_errors=True)

    result["run_dir"] = run_dir.as_posix() if not should_cleanup else "[temporary cleaned]"
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_summary(result)
    return 0


def run_flow(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    _configure_isolated_runtime(run_dir)

    from fastapi.testclient import TestClient

    from dream.api.app import create_app

    client = TestClient(create_app())
    source_path = _resolve_repo_path(args.source)

    upload = _post(
        client,
        "/intake/documents",
        {
            "team_id": args.team,
            "file_path": source_path.as_posix(),
            "document_type": "runbooks",
        },
    )
    document_id = _expect_text(upload, "document_id")
    source_hash = _expect_text(upload, "source_hash")
    _expect(source_hash.startswith("sha256:"), "upload response did not include source hash")

    draft = _post(client, f"/intake/documents/{document_id}/parse", {})
    draft_id = _expect_text(draft, "draft_id")
    sections = _expect_list(draft, "sections")
    _expect(sections, "parse did not produce sections")
    _expect(
        all(section.get("section_hash", "").startswith("sha256:") for section in sections),
        "parsed sections are missing section hashes",
    )
    _expect(
        all(section.get("source_span") for section in sections),
        "parsed sections are missing source spans",
    )

    metadata = _patch(
        client,
        f"/intake/drafts/{draft_id}/metadata",
        {
            "title": args.title,
            "target_doc_type": args.target_doc_type,
            "app": args.app,
            "component": args.component,
            "concepts": ["output reconciliation", "retry coverage", "source traceability"],
            "reviewer": "acceptance-script",
            "notes": "Acceptance metadata normalization.",
        },
    )
    _expect(metadata["target_doc_type"] == args.target_doc_type, "metadata doc type mismatch")

    reviewed = _post(
        client,
        f"/intake/drafts/{draft_id}/review",
        {
            "status": "approved",
            "reviewer": "acceptance-script",
            "notes": "Acceptance review approved deterministic raw-doc parse.",
        },
    )
    _expect(reviewed["review_status"] == "approved", "draft review did not approve")

    promoted = _post(client, f"/intake/drafts/{draft_id}/promote", {})
    promoted_path = _expect_text(promoted, "promoted_path")
    _expect(promoted["status"] == "promoted", "draft promotion did not finish")
    _expect(f"/docs/{args.target_doc_type}/" in promoted_path, "promoted path is wrong")

    review_events = _get(client, f"/intake/drafts/{draft_id}/review-events")
    event_types = {event["event_type"] for event in review_events}
    _expect(
        event_types == {"metadata_update", "review_decision", "promotion"},
        f"unexpected review event types: {sorted(event_types)}",
    )
    metadata_event = _first_event(review_events, "metadata_update")
    diff_fields = {diff["field"] for diff in metadata_event["metadata_diff"]}
    _expect(
        {"title", "target_doc_type", "app", "component", "concepts"}.issubset(diff_fields),
        f"metadata event is missing field diffs: {sorted(diff_fields)}",
    )
    _expect(
        metadata_event["audit_run_id"] == f"intake-metadata-{draft_id}",
        "metadata review event is not linked to its audit run",
    )

    draft_detail_before_downstream = _get(client, f"/intake/documents/{document_id}/detail")
    _verify_detail_provenance(
        draft_detail_before_downstream,
        document_id=document_id,
        draft_id=draft_id,
        source_hash=source_hash,
    )

    requirement_draft = _post(
        client,
        "/requirements/draft",
        {
            "team_id": args.team,
            "app": args.app,
            "component": args.component,
            "rough_business_request": args.query,
            "top_k": 5,
            "llm_provider": "mock",
        },
    )
    requirement_run_id = _expect_text(requirement_draft, "run_id")
    _expect(
        promoted_path in requirement_draft.get("sources_used", []),
        "downstream requirement draft did not retrieve the promoted structured doc",
    )
    audit_run = _get(client, f"/audit/runs/{requirement_run_id}")
    _expect(
        promoted_path in audit_run.get("retrieved_source_paths", []),
        "audit run does not record promoted doc as retrieved source",
    )

    detail_after_downstream = _get(client, f"/intake/documents/{document_id}/detail")
    downstream_usage = _find_downstream_usage(detail_after_downstream, requirement_run_id)
    proof = downstream_usage["match_proofs"][0]
    _expect(proof["document_id"] == document_id, "downstream proof lost document id")
    _expect(proof["draft_id"] == draft_id, "downstream proof lost draft id")
    _expect(proof["source_hash"] == source_hash, "downstream proof lost source hash")
    _expect(proof["source_hash_verified"] is True, "downstream proof did not verify hash")
    _expect(proof["section_proofs"], "downstream proof is missing section proofs")

    scan = _post(
        client,
        "/memory/scan",
        {
            "team_id": args.team,
            "repo_path": args.repo_path,
            "repo_name": args.repo_name,
        },
    )
    scan_id = _expect_text(scan, "scan_id")
    claim, intake_proof = _find_claim_with_intake_proof(scan, document_id)
    _expect(intake_proof["draft_id"] == draft_id, "memory proof lost draft id")
    _expect(intake_proof["promoted_path"] == promoted_path, "memory proof lost promoted path")
    _expect(intake_proof["source_hash_verified"] is True, "memory proof did not verify hash")
    _expect(intake_proof["section_proofs"], "memory proof is missing section proofs")
    _expect(intake_proof["match_explanation"], "memory proof is missing match explanation")
    _expect(intake_proof["matched_terms"], "memory proof is missing matched terms")
    intake_audit_run_ids = intake_proof["intake_audit_run_ids"]
    _expect(
        any(run_id.startswith("intake-promote-") for run_id in intake_audit_run_ids),
        "memory proof is missing intake promotion audit run id",
    )

    review_claim = _post(
        client,
        "/memory/review",
        {
            "team_id": args.team,
            "scan_id": scan_id,
            "claim_id": claim["claim_id"],
            "status": "approved",
            "reviewer": "acceptance-script",
            "reason": "Acceptance validated raw-doc proof traceability.",
        },
    )
    _expect(review_claim["new_status"] == "approved", "memory claim review did not approve")

    context_case = _post(
        client,
        "/requirement-cases",
        {
            "team_id": args.team,
            "raw_request": claim["entity"]["canonical_name"],
            "created_by_role": "BA",
        },
    )
    case_id = context_case["case"]["case_id"]
    context_trail = _get(client, f"/context/trails/{case_id}")
    used_claim = _find_used_claim(context_trail, claim["claim_id"])
    used_proof = used_claim["intake_proofs"][0]
    _expect(used_proof["document_id"] == document_id, "context trail lost document proof")
    _expect(
        used_proof["section_proofs"][0]["section_hash"].startswith("sha256:"),
        "context trail proof lost section hash",
    )

    diff = _get(client, "/memory/diff", {"team_id": args.team, "scan_id": scan_id})
    diff_markdown = diff.get("markdown", "")
    _expect(f"intake proof: {document_id}" in diff_markdown, "memory diff lacks intake proof")

    return {
        "ok": True,
        "document_id": document_id,
        "draft_id": draft_id,
        "source_hash": source_hash,
        "promoted_path": promoted_path,
        "review_event_types": sorted(event_types),
        "metadata_diff_fields": sorted(diff_fields),
        "downstream_run_id": requirement_run_id,
        "scan_id": scan_id,
        "claim_id": claim["claim_id"],
        "context_case_id": case_id,
        "proof_match_explanation": intake_proof["match_explanation"],
        "proof_matched_terms": intake_proof["matched_terms"],
    }


def _prepare_run_dir(work_dir: Path | None, keep_artifacts: bool) -> tuple[Path, bool]:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    if work_dir is None:
        return Path(tempfile.mkdtemp(prefix="dream-raw-doc-flow-")), not keep_artifacts
    base = work_dir.resolve()
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"dream-raw-doc-flow-{timestamp}"
    run_dir.mkdir()
    return run_dir, False


def _configure_isolated_runtime(run_dir: Path) -> None:
    knowledge_root = run_dir / "knowledge_packs"
    shutil.copytree(PROJECT_ROOT / "knowledge_packs", knowledge_root)
    artifact_root = run_dir / "artifacts"
    audit_path = run_dir / "dream.sqlite"
    config_path = run_dir / "dream.yaml"
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
    os.environ["DREAM_CONFIG_FILE"] = str(config_path)
    os.environ["DREAM_ARTIFACT_ROOT"] = str(artifact_root)
    os.environ["DREAM_AUDIT_DB_PATH"] = str(audit_path)


def _resolve_repo_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _post(client: Any, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    return _json_or_raise(response, path)


def _patch(client: Any, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.patch(path, json=payload)
    return _json_or_raise(response, path)


def _get(client: Any, path: str, params: dict[str, Any] | None = None) -> Any:
    response = client.get(path, params=params)
    return _json_or_raise(response, path)


def _json_or_raise(response: Any, path: str) -> Any:
    if response.status_code >= 400:
        raise AcceptanceError(f"{path} returned {response.status_code}: {response.text}")
    return response.json()


def _verify_detail_provenance(
    detail: dict[str, Any],
    *,
    document_id: str,
    draft_id: str,
    source_hash: str,
) -> None:
    _expect(detail["document"]["document_id"] == document_id, "detail lost document id")
    _expect(detail["draft"]["draft_id"] == draft_id, "detail lost draft id")
    _expect(detail["draft"]["review_status"] == "promoted", "detail draft is not promoted")
    _expect(detail["source_hash_verified"] is True, "detail source hash did not verify")
    _expect(source_hash == detail["document"]["source_hash"], "detail source hash mismatch")
    _expect(detail["raw_text"], "detail raw text is empty")
    audit_use_cases = {event["use_case"] for event in detail["audit_events"]}
    _expect(
        {
            "knowledge_intake_upload",
            "knowledge_intake_parse",
            "knowledge_intake_metadata_update",
            "knowledge_intake_review",
            "knowledge_intake_promote",
        }.issubset(audit_use_cases),
        f"detail audit events are incomplete: {sorted(audit_use_cases)}",
    )
    _expect(
        {event["event_type"] for event in detail["review_events"]}
        == {"metadata_update", "review_decision", "promotion"},
        "detail review events are incomplete",
    )


def _first_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in events:
        if event["event_type"] == event_type:
            return event
    raise AcceptanceError(f"missing review event: {event_type}")


def _find_downstream_usage(detail: dict[str, Any], run_id: str) -> dict[str, Any]:
    for usage in detail["downstream_usages"]:
        if usage["audit_record"]["run_id"] == run_id:
            return usage
    raise AcceptanceError(f"downstream usage not found for run: {run_id}")


def _find_claim_with_intake_proof(
    scan: dict[str, Any],
    document_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for claim in scan["claims"]:
        for proof in claim["evidence"].get("intake_proofs", []):
            if proof["document_id"] == document_id:
                return claim, proof
    raise AcceptanceError(f"memory scan did not produce intake proof for {document_id}")


def _find_used_claim(context_trail: dict[str, Any], claim_id: str) -> dict[str, Any]:
    for claim in context_trail["memory_claims_used"]:
        if claim["claim_id"] == claim_id:
            return claim
    raise AcceptanceError(f"context trail did not use approved claim: {claim_id}")


def _expect(condition: Any, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _expect_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AcceptanceError(f"expected non-empty string at key: {key}")
    return value


def _expect_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise AcceptanceError(f"expected list at key: {key}")
    return value


def _print_summary(result: dict[str, Any]) -> None:
    print("PASS raw-doc-memory-flow")
    for key in [
        "document_id",
        "draft_id",
        "source_hash",
        "promoted_path",
        "review_event_types",
        "metadata_diff_fields",
        "downstream_run_id",
        "scan_id",
        "claim_id",
        "context_case_id",
        "run_dir",
    ]:
        print(f"{key}: {result[key]}")
    print(f"proof_match_explanation: {result['proof_match_explanation']}")
    print(f"proof_matched_terms: {', '.join(result['proof_matched_terms'])}")


if __name__ == "__main__":
    raise SystemExit(main())
