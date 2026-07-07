# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from dream.memory import MemoryClaimRetriever, MemoryDistillationService
from dream.memory.repository import MemoryDistillationRepository

DEFAULT_TEAM_ID = "demo_team"
DEFAULT_REPO_PATH = "examples/dfp-demo-repo"
DEFAULT_REPO_NAME = "dfp-demo-repo"
DEFAULT_QUERY = "execution status output collection partial completion"
REVIEWER = "qwencloud-demo-seed"
REASON = "Seeded for the Qwen Cloud hackathon judge flow from source-backed synthetic DFP memory."


def main() -> int:
    args = parse_args()
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")[:-3]
    output_dir = Path(args.output_dir)
    package_dir = output_dir / f"seeded-demo-artifact-{timestamp}"
    artifact_root = (
        Path(args.artifact_root) if args.artifact_root else package_dir / "artifact-root"
    )
    audit_db_path = artifact_root / "dream-seeded-demo.sqlite"

    package_dir.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    os.environ["DREAM_ARTIFACT_ROOT"] = str(artifact_root)
    os.environ["DREAM_AUDIT_DB_PATH"] = str(audit_db_path)

    repository = MemoryDistillationRepository(artifact_root)
    service = MemoryDistillationService(repository=repository)
    scan = service.scan(
        team_id=args.team,
        repo_path=args.repo,
        repo_name=args.repo_name,
    )
    selected_claims = select_seed_claims(scan.claims, promote_count=args.promote_count)
    events = [
        service.review_claim(
            team_id=args.team,
            claim_id=claim.claim_id,
            new_status="approved",
            reviewer=REVIEWER,
            reason=REASON,
            scan_id=scan.scan_id,
        )
        for claim in selected_claims
    ]

    retriever = MemoryClaimRetriever(repository=repository)
    search_results = retriever.search(
        team_id=args.team,
        query=args.query,
        scan_id=scan.scan_id,
        top_k=args.top_k,
    )
    context_card = retriever.context_card(
        team_id=args.team,
        query=args.query,
        scan_id=scan.scan_id,
        top_k=args.top_k,
    )

    context_path = package_dir / "seeded-demo-context-card.md"
    context_path.write_text(context_card, encoding="utf-8")
    summary = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "status": "READY" if events and search_results else "DRAFT",
        "teamId": args.team,
        "repoPath": args.repo,
        "repoName": args.repo_name,
        "query": args.query,
        "artifactRoot": artifact_root.as_posix(),
        "scanId": scan.scan_id,
        "scanPath": repository.scan_path(args.team, scan.scan_id).as_posix(),
        "latestScanPath": repository.latest_scan_path(args.team).as_posix(),
        "ledgerPath": repository.ledger_path(args.team).as_posix(),
        "contextCardPath": context_path.as_posix(),
        "sources": len(scan.sources),
        "claims": len(scan.claims),
        "selectedClaims": [
            {
                "claimId": claim.claim_id,
                "entity": claim.entity.canonical_name,
                "relationType": claim.relation.type,
                "relationValue": claim.relation.value
                or claim.relation.object_entity_id
                or "",
                "evidencePaths": [span.path for span in claim.evidence.spans],
            }
            for claim in selected_claims
        ],
        "reviewEvents": [
            {
                "eventId": event.event_id,
                "claimId": event.claim_id,
                "previousStatus": event.previous_status,
                "newStatus": event.new_status,
                "reviewerSignature": event.reviewer_signature,
            }
            for event in events
        ],
        "searchResultCount": len(search_results),
        "searchResultClaimIds": [result.claim.claim_id for result in search_results],
        "readyForJudgeDemo": bool(events and search_results),
    }
    summary_json = package_dir / "seeded-demo-summary.json"
    summary_md = package_dir / "README.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(render_markdown(summary), encoding="utf-8")
    zip_path = shutil.make_archive(str(package_dir), "zip", package_dir)
    summary["zipPath"] = zip_path
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Seeded demo artifact {summary['status']}: {summary_md}")
    print(f"JSON: {summary_json}")
    print(f"ZIP: {zip_path}")
    return 0 if summary["readyForJudgeDemo"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a seeded DREAM MemoryAgent demo artifact for Qwen Cloud judges."
    )
    parser.add_argument("--team", default=DEFAULT_TEAM_ID)
    parser.add_argument("--repo", default=DEFAULT_REPO_PATH)
    parser.add_argument("--repo-name", default=DEFAULT_REPO_NAME)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--output-dir", default="artifacts/qwencloud-proof")
    parser.add_argument("--artifact-root", default="")
    parser.add_argument("--promote-count", type=int, default=6)
    parser.add_argument("--top-k", type=int, default=8)
    return parser.parse_args()


def select_seed_claims(claims: list[object], *, promote_count: int) -> list[object]:
    candidates = [
        claim
        for claim in claims
        if getattr(claim.governance, "status", "") == "candidate"
        and getattr(claim.extraction, "method", "") == "heuristic_semantic"
        and claim.evidence.spans
        and getattr(claim.security, "classification", "") == "public_demo"
    ]
    ranked = sorted(candidates, key=claim_rank)
    return ranked[:promote_count]


def claim_rank(claim: object) -> tuple[int, str, str]:
    path_text = " ".join(span.path for span in claim.evidence.spans).lower()
    value_text = " ".join(
        [
            claim.entity.canonical_name,
            claim.relation.type,
            claim.relation.value or "",
            claim.relation.object_entity_id or "",
            path_text,
        ]
    ).lower()
    priority = 20
    if "execution" in value_text or "status" in value_text:
        priority -= 8
    if "output" in value_text or "collection" in value_text:
        priority -= 6
    if "partial" in value_text or "recovery" in value_text:
        priority -= 4
    if "knowledge_packs/demo_team/docs" in path_text:
        priority -= 3
    return priority, claim.entity.canonical_name, claim.claim_id


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Qwen Cloud Seeded Demo Artifact",
        "",
        f"- Status: {summary['status']}",
        f"- Team: `{summary['teamId']}`",
        f"- Repo: `{summary['repoPath']}`",
        f"- Scan: `{summary['scanId']}`",
        f"- Artifact root: `{summary['artifactRoot']}`",
        f"- Sources: {summary['sources']}",
        f"- Claims: {summary['claims']}",
        f"- Approved seed claims: {len(summary['reviewEvents'])}",
        f"- Search result count: {summary['searchResultCount']}",
        f"- Context card: `{summary['contextCardPath']}`",
        "",
        "## Judge Flow",
        "",
        "1. Start DREAM with this artifact root:",
        "",
        "```powershell",
        f'$env:DREAM_ARTIFACT_ROOT="{summary["artifactRoot"]}"',
        "uvicorn dream.api.app:app --host 127.0.0.1 --port 8000",
        "```",
        "",
        "2. Open `/hackathon-demo`, then Memory Hub. The latest memory scan and",
        "   approval ledger are already present, so approved memory search/context",
        "   can be demonstrated without manual claim approval first.",
        "",
        "3. Show the generated context card:",
        "",
        f"`{summary['contextCardPath']}`",
        "",
        "## Approved Seed Claims",
        "",
    ]
    for item in summary["selectedClaims"]:
        lines.append(
            f"- `{item['claimId']}` {item['entity']} --{item['relationType']}--> "
            f"{item['relationValue'] or '_'}"
        )
        lines.append(f"  - evidence: {', '.join(item['evidencePaths'][:3])}")
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
