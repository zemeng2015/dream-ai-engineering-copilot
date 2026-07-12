#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: Any
    headers: dict[str, str]
    latency_ms: int


def seed(
    *,
    base_url: str,
    expected_build: str,
    state_file: Path,
    provider: str = "qwen-cloud",
    timeout: float = 120.0,
) -> dict[str, Any]:
    normalized_url = _normalize_base_url(base_url)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid4().hex[:8]}"
    scope = {
        "teamId": "fc-persistence-proof",
        "userId": f"run-{run_id.lower()}",
    }
    query = "What must happen before shifting production traffic?"

    health = _assert_health(
        _request_json(normalized_url, "/health", timeout=timeout),
        expected_build=expected_build,
    )
    capture = _request_json(
        normalized_url,
        "/experience/capture",
        method="POST",
        payload={
            "team_id": scope["teamId"],
            "user_id": scope["userId"],
            "session_id": "session-qwen-seed",
            "observation": (
                "Remember this durable engineering preference for future sessions: "
                "before shifting production traffic, run and verify database migrations."
            ),
            "source_reference": f"fc-proof:{run_id}",
            "llm_provider": provider,
        },
        timeout=timeout,
    )
    capture_summary = _assert_qwen_capture(capture, expected_provider=provider)
    memory_id = capture_summary["memoryId"]
    decision_id = capture_summary["decisionId"]

    recall = _recall(
        normalized_url,
        scope=scope,
        memory_id=memory_id,
        query=query,
        timeout=timeout,
    )
    decisions = _list_records(
        normalized_url,
        "/experience/decisions",
        scope=scope,
        timeout=timeout,
    )
    matching_decisions = [
        item for item in decisions if item.get("decision_id") == decision_id
    ]
    if len(matching_decisions) != 1:
        raise RuntimeError("The Qwen decision receipt was not durable after capture.")

    state = {
        "schemaVersion": "dream-fc-persistence-seed-v1",
        "runId": run_id,
        "seededAt": datetime.now(UTC).isoformat(),
        "baseUrl": normalized_url,
        "expectedBuild": expected_build,
        "scope": scope,
        "query": query,
        "seedRuntime": health,
        "capture": capture_summary,
        "recall": recall,
        "credentials": {"valuesRecorded": False},
    }
    state_file = state_file.expanduser().resolve()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


def verify(
    *,
    base_url: str,
    state_file: Path,
    output_dir: Path,
    timeout: float = 120.0,
) -> tuple[dict[str, Any], Path]:
    normalized_url = _normalize_base_url(base_url)
    state = json.loads(state_file.expanduser().resolve().read_text(encoding="utf-8"))
    if state.get("schemaVersion") != "dream-fc-persistence-seed-v1":
        raise RuntimeError("Unsupported FC persistence seed schema.")
    if state.get("baseUrl") != normalized_url:
        raise RuntimeError("Seed and verification base URLs do not match.")

    expected_build = _required_string(state, "expectedBuild")
    seed_runtime = _required_mapping(state, "seedRuntime")
    seed_instance = _required_string(seed_runtime, "instanceId")
    scope = _required_mapping(state, "scope")
    capture = _required_mapping(state, "capture")
    memory_id = _required_string(capture, "memoryId")
    decision_id = _required_string(capture, "decisionId")

    health = _assert_health(
        _request_json(normalized_url, "/health", timeout=timeout),
        expected_build=expected_build,
    )
    verify_instance = _required_string(health, "instanceId")
    if verify_instance == seed_instance:
        raise RuntimeError(
            "FC instance ID did not change; redeploy or recycle the instance before verify."
        )

    memories = _list_records(
        normalized_url,
        "/experience/memories",
        scope=scope,
        timeout=timeout,
        include_inactive=True,
    )
    matching_memories = [item for item in memories if item.get("memory_id") == memory_id]
    if len(matching_memories) != 1:
        raise RuntimeError("The seeded memory was not found after the FC instance changed.")
    memory = matching_memories[0]
    if memory.get("status") != "active":
        raise RuntimeError("The seeded memory is no longer active after FC redeployment.")
    if memory.get("key") != capture.get("memoryKey") or memory.get("value") != capture.get(
        "memoryValue"
    ):
        raise RuntimeError("The reloaded memory payload differs from the Qwen-created value.")

    decisions = _list_records(
        normalized_url,
        "/experience/decisions",
        scope=scope,
        timeout=timeout,
    )
    matching_decisions = [
        item for item in decisions if item.get("decision_id") == decision_id
    ]
    if len(matching_decisions) != 1:
        raise RuntimeError("The Qwen decision was not found after the FC instance changed.")
    decision = matching_decisions[0]
    receipt = _required_mapping(decision, "llm_receipt")
    seed_receipt = _required_mapping(capture, "llmReceipt")
    for field in ("request_sha256", "response_sha256", "provider_request_id"):
        if receipt.get(field) != seed_receipt.get(field):
            raise RuntimeError(f"The persisted Qwen receipt changed field: {field}.")

    recall = _recall(
        normalized_url,
        scope=scope,
        memory_id=memory_id,
        query=_required_string(state, "query"),
        timeout=timeout,
    )
    proof = {
        "schemaVersion": "dream-fc-persistence-proof-v1",
        "status": "pass",
        "generatedAt": datetime.now(UTC).isoformat(),
        "runId": _required_string(state, "runId"),
        "baseUrl": normalized_url,
        "buildSha": expected_build,
        "runtimeTransition": {
            "seedInstanceId": seed_instance,
            "verifyInstanceId": verify_instance,
            "instanceChanged": True,
        },
        "storage": {
            "backend": health["storageBackend"],
            "durable": health["storageDurable"],
            "transactionMode": health["transactionMode"],
            "region": health["region"],
            "service": health["service"],
        },
        "qwen": {
            "provider": capture["provider"],
            "model": capture["model"],
            "action": capture["action"],
            "requestSha256": seed_receipt["request_sha256"],
            "responseSha256": seed_receipt["response_sha256"],
            "providerRequestId": seed_receipt.get("provider_request_id"),
            "latencyMs": seed_receipt["latency_ms"],
            "tokenUsage": capture["tokenUsage"],
        },
        "persistence": {
            "scope": scope,
            "memoryId": memory_id,
            "decisionId": decision_id,
            "memoryKey": memory["key"],
            "memoryValue": memory["value"],
            "memoryStatus": memory["status"],
            "memoryCount": len(memories),
            "decisionCount": len(decisions),
            "recallSelectedMemoryIds": recall["selectedMemoryIds"],
        },
        "credentials": {"valuesRecorded": False},
    }
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = proof["runId"]
    output_path = output_dir / f"fc-persistence-proof-{run_id}.json"
    latest_path = output_dir / "fc-persistence-proof-latest.json"
    rendered = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    output_path.write_text(rendered, encoding="utf-8")
    latest_path.write_text(rendered, encoding="utf-8")
    return proof, output_path


def _assert_health(result: HttpResult, *, expected_build: str) -> dict[str, Any]:
    body = _mapping(result.body, "health response")
    checks = {
        "experience_storage_backend": "tablestore",
        "experience_storage_durable": True,
        "experience_transaction_mode": "partition-local-transaction",
        "llm_provider": "qwen-cloud",
        "llm_api_key_configured": True,
        "build_sha": expected_build,
    }
    for field, expected in checks.items():
        if body.get(field) != expected:
            raise RuntimeError(
                f"Health proof mismatch for {field}: expected {expected!r}, "
                f"received {body.get(field)!r}."
            )
    instance_id = body.get("runtime_instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        raise RuntimeError("Health response does not expose an FC instance ID.")
    if result.headers.get("x-dream-build-sha") != expected_build:
        raise RuntimeError("X-Dream-Build-Sha does not match the deployed commit.")
    if result.headers.get("x-dream-fc-instance-id") != instance_id:
        raise RuntimeError("FC instance header and health payload do not match.")
    return {
        "instanceId": instance_id,
        "buildSha": expected_build,
        "storageBackend": body["experience_storage_backend"],
        "storageDurable": body["experience_storage_durable"],
        "transactionMode": body["experience_transaction_mode"],
        "region": body.get("alibaba_cloud_region"),
        "service": body.get("alibaba_cloud_service"),
        "provider": body["llm_provider"],
        "model": body.get("llm_model"),
        "latencyMs": result.latency_ms,
    }


def _assert_qwen_capture(
    result: HttpResult,
    *,
    expected_provider: str,
) -> dict[str, Any]:
    body = _mapping(result.body, "capture response")
    decision = _required_mapping(body, "decision")
    memory = _required_mapping(body, "memory")
    receipt = _required_mapping(decision, "llm_receipt")
    if decision.get("action") not in {"remember", "supersede"}:
        raise RuntimeError("Qwen did not create an active durable memory.")
    if decision.get("provider_name") != expected_provider:
        raise RuntimeError("Capture decision was not produced by the requested Qwen provider.")
    if memory.get("status") != "active":
        raise RuntimeError("Qwen-created memory is not active.")
    memory_id = _required_string(memory, "memory_id")
    if decision.get("created_memory_id") != memory_id:
        raise RuntimeError("Decision and created memory IDs do not match.")
    for field in ("request_sha256", "response_sha256"):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise RuntimeError(f"Qwen receipt has an invalid {field}.")
    endpoint_host = receipt.get("endpoint_host")
    if not isinstance(endpoint_host, str) or "aliyuncs.com" not in endpoint_host:
        raise RuntimeError("Qwen receipt is not from an Alibaba Cloud endpoint.")
    token_usage = decision.get("token_usage")
    if not isinstance(token_usage, dict) or not token_usage:
        raise RuntimeError("Qwen capture did not return token usage.")
    return {
        "decisionId": _required_string(decision, "decision_id"),
        "memoryId": memory_id,
        "memoryKey": _required_string(memory, "key"),
        "memoryValue": _required_string(memory, "value"),
        "action": decision["action"],
        "provider": decision["provider_name"],
        "model": _required_string(decision, "model_name"),
        "tokenUsage": token_usage,
        "llmReceipt": receipt,
        "requestInstanceId": result.headers.get("x-dream-fc-instance-id"),
        "requestLatencyMs": result.latency_ms,
    }


def _recall(
    base_url: str,
    *,
    scope: dict[str, Any],
    memory_id: str,
    query: str,
    timeout: float,
) -> dict[str, Any]:
    response = _request_json(
        base_url,
        "/experience/recall",
        method="POST",
        payload={
            "team_id": _required_string(scope, "teamId"),
            "user_id": _required_string(scope, "userId"),
            "session_id": "session-persistence-verify",
            "query": query,
            "token_budget": 256,
            "limit": 10,
        },
        timeout=timeout,
    )
    body = _mapping(response.body, "recall response")
    selected = body.get("selected")
    if not isinstance(selected, list):
        raise RuntimeError("Recall response does not contain a selected list.")
    selected_ids = [
        item.get("memory", {}).get("memory_id")
        for item in selected
        if isinstance(item, dict) and isinstance(item.get("memory"), dict)
    ]
    if memory_id not in selected_ids:
        raise RuntimeError("The Qwen-created memory was not recalled from Tablestore.")
    return {
        "selectedMemoryIds": selected_ids,
        "estimatedTokensUsed": body.get("estimated_tokens_used"),
        "requestInstanceId": response.headers.get("x-dream-fc-instance-id"),
        "requestLatencyMs": response.latency_ms,
    }


def _list_records(
    base_url: str,
    path: str,
    *,
    scope: dict[str, Any],
    timeout: float,
    include_inactive: bool | None = None,
) -> list[dict[str, Any]]:
    query: dict[str, str] = {
        "team_id": _required_string(scope, "teamId"),
        "user_id": _required_string(scope, "userId"),
    }
    if include_inactive is not None:
        query["include_inactive"] = str(include_inactive).lower()
    response = _request_json(
        base_url,
        f"{path}?{urllib.parse.urlencode(query)}",
        timeout=timeout,
    )
    if not isinstance(response.body, list) or not all(
        isinstance(item, dict) for item in response.body
    ):
        raise RuntimeError(f"{path} did not return a JSON object list.")
    return response.body


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> HttpResult:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "DREAM-QwenCloud-Persistence-Proof/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            elapsed = round((time.monotonic() - started) * 1000)
            return HttpResult(
                status=response.status,
                body=json.loads(raw),
                headers={key.lower(): value for key, value in response.headers.items()},
                latency_ms=elapsed,
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Base URL must be an absolute HTTPS URL.")
    return normalized


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected {label} to be a JSON object.")
    return value


def _required_mapping(value: dict[str, Any], field: str) -> dict[str, Any]:
    return _mapping(value.get(field), field)


def _required_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise RuntimeError(f"Missing required string field: {field}.")
    return item


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove Qwen-created memory survives an FC instance replacement."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed")
    seed_parser.add_argument("--base-url", required=True)
    seed_parser.add_argument("--expected-build", required=True)
    seed_parser.add_argument(
        "--state-file",
        default="artifacts/qwencloud-proof/fc-persistence/seed-state.json",
    )
    seed_parser.add_argument("--provider", default="qwen-cloud")
    seed_parser.add_argument("--timeout", type=float, default=120.0)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--base-url", required=True)
    verify_parser.add_argument(
        "--state-file",
        default="artifacts/qwencloud-proof/fc-persistence/seed-state.json",
    )
    verify_parser.add_argument(
        "--output-dir",
        default="artifacts/qwencloud-proof/fc-persistence",
    )
    verify_parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "seed":
        state = seed(
            base_url=args.base_url,
            expected_build=args.expected_build,
            state_file=Path(args.state_file),
            provider=args.provider,
            timeout=args.timeout,
        )
        print(
            json.dumps(
                {
                    "status": "seeded",
                    "runId": state["runId"],
                    "instanceId": state["seedRuntime"]["instanceId"],
                    "memoryId": state["capture"]["memoryId"],
                    "provider": state["capture"]["provider"],
                    "model": state["capture"]["model"],
                    "stateFile": str(Path(args.state_file).expanduser().resolve()),
                },
                indent=2,
            )
        )
        return 0

    proof, output_path = verify(
        base_url=args.base_url,
        state_file=Path(args.state_file),
        output_dir=Path(args.output_dir),
        timeout=args.timeout,
    )
    print(
        json.dumps(
            {
                "status": proof["status"],
                "runId": proof["runId"],
                "instanceChanged": proof["runtimeTransition"]["instanceChanged"],
                "memoryId": proof["persistence"]["memoryId"],
                "output": str(output_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
