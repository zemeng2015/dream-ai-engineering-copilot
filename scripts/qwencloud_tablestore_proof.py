#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Lock
from typing import Any

from dotenv import dotenv_values
from tablestore import OTSClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dream.experience.models import (  # noqa: E402
    ExperienceObservation,
    ExperiencePolicyResult,
    MemoryActionProposal,
)
from dream.experience.service import ExperienceMemoryService  # noqa: E402
from dream.experience.tablestore_repository import (  # noqa: E402
    TablestoreExperienceMemoryRepository,
)


class CountingTablestoreClient:
    def __init__(self, client: OTSClient) -> None:
        self.client = client
        self._lock = Lock()
        self.transaction_start_attempts = 0
        self.transaction_start_conflicts = 0

    def start_local_transaction(self, *args: Any, **kwargs: Any) -> str:
        with self._lock:
            self.transaction_start_attempts += 1
        try:
            return self.client.start_local_transaction(*args, **kwargs)
        except Exception:
            with self._lock:
                self.transaction_start_conflicts += 1
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self.client, name)


def main() -> int:
    args = _parse_args()
    settings = _load_settings(args.env_file)
    region = args.region or _setting(settings, "ALIBABA_CLOUD_RUNTIME_REGION")
    region = region or "ap-southeast-1"
    endpoint = args.endpoint or _setting(settings, "ALIBABA_TABLESTORE_ENDPOINT")
    endpoint = endpoint or f"https://dreammem.{region}.ots.aliyuncs.com"
    instance = args.instance or _setting(settings, "ALIBABA_TABLESTORE_INSTANCE")
    instance = instance or "dreammem"
    table = args.table or _setting(settings, "ALIBABA_TABLESTORE_TABLE")
    table = table or "dream_experience_v1"
    access_key_id = _required_setting(settings, "ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = _required_setting(
        settings,
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    )
    security_token = _setting(settings, "ALIBABA_CLOUD_SECURITY_TOKEN")

    client = CountingTablestoreClient(
        OTSClient(
            endpoint,
            access_key_id,
            access_key_secret,
            instance,
            sts_token=security_token,
            region=region,
            max_connection=max(100, args.concurrency * 4),
            enable_native=False,
        )
    )
    repository = TablestoreExperienceMemoryRepository(
        client=client,
        table_name=table,
        transaction_attempts=40,
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    started = time.monotonic()
    table_description = _describe_table(client, table)
    round_trip = _round_trip(repository, run_id)
    concurrency = _concurrency_proof(repository, run_id, args.concurrency)
    duration = round(time.monotonic() - started, 3)

    proof = {
        "schemaVersion": "dream-tablestore-proof-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "runId": run_id,
        "backend": repository.backend_name,
        "durable": repository.durable,
        "region": region,
        "instance": instance,
        "table": table,
        "endpoint": endpoint,
        "transactionMode": "partition-local-transaction",
        "durationSeconds": duration,
        "tableDescription": table_description,
        "roundTrip": round_trip,
        "concurrency": concurrency,
        "credentials": {
            "source": "environment-or-local-ignored-env-file",
            "valuesRecorded": False,
        },
    }
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / f"tablestore-proof-{run_id}.json"
    latest_path = output_dir / "tablestore-proof-latest.json"
    rendered = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    run_path.write_text(rendered, encoding="utf-8")
    latest_path.write_text(rendered, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "pass",
                "runId": run_id,
                "output": str(run_path),
                "roundTripActive": round_trip["activeCount"],
                "concurrentRequests": concurrency["requestsSucceeded"],
                "concurrentActive": concurrency["activeCount"],
                "concurrentSuperseded": concurrency["supersededCount"],
                "decisionCount": concurrency["decisionCount"],
                "durationSeconds": duration,
            },
            indent=2,
        )
    )
    return 0


def _describe_table(client: CountingTablestoreClient, table: str) -> dict[str, Any]:
    response = client.describe_table(table)
    capacity = response.reserved_throughput_details.capacity_unit
    return {
        "requestId": response.request_id,
        "primaryKey": [
            {"name": name, "type": value_type}
            for name, value_type in response.table_meta.schema_of_primary_key
        ],
        "timeToLive": response.table_options.time_to_live,
        "maxVersions": response.table_options.max_version,
        "allowUpdates": response.table_options.allow_update,
        "reservedReadCU": capacity.read,
        "reservedWriteCU": capacity.write,
        "secondaryIndexCount": len(response.secondary_indexes),
        "localTransactionVerifiedBySuccessfulCommit": True,
    }


def _round_trip(
    repository: TablestoreExperienceMemoryRepository,
    run_id: str,
) -> dict[str, Any]:
    team_id = "cloud-roundtrip-proof"
    user_id = f"roundtrip-{run_id.lower()}"
    service = ExperienceMemoryService(repository=repository)
    result = service.apply_policy_result(
        ExperienceObservation(
            team_id=team_id,
            user_id=user_id,
            session_id="session-seed",
            observation="Use the durable Tablestore deployment mode.",
        ),
        ExperiencePolicyResult(
            proposal=MemoryActionProposal(
                action="remember",
                kind="preference",
                key="deployment_mode",
                value="tablestore-partition-transaction",
                confidence=1.0,
                importance=5,
                rationale="Real Alibaba Cloud persistence round-trip proof.",
            ),
            provider_name="cloud-proof",
            model_name="deterministic-contract",
        ),
    )
    memories = ExperienceMemoryService(repository=repository).list_memories(
        team_id=team_id,
        user_id=user_id,
        include_inactive=True,
    )
    decisions = repository.list_decisions(team_id=team_id, user_id=user_id)
    if result.memory is None or len(memories) != 1 or len(decisions) != 1:
        raise RuntimeError("Tablestore round-trip contract failed.")
    if memories[0].memory_id != result.memory.memory_id or memories[0].status != "active":
        raise RuntimeError("Tablestore round-trip returned a different current memory.")
    return {
        "scope": {"teamId": team_id, "userId": user_id},
        "memoryId": result.memory.memory_id,
        "value": memories[0].value,
        "memoryCount": len(memories),
        "decisionCount": len(decisions),
        "activeCount": result.active_memory_count,
    }


def _concurrency_proof(
    repository: TablestoreExperienceMemoryRepository,
    run_id: str,
    concurrency: int,
) -> dict[str, Any]:
    service = ExperienceMemoryService(repository=repository)
    team_id = "cloud-concurrency-proof"
    user_id = f"barrier-{run_id.lower()}"
    barrier = Barrier(concurrency)
    client = repository.client
    attempts_before = client.transaction_start_attempts
    conflicts_before = client.transaction_start_conflicts

    def write(index: int) -> tuple[str, str | None]:
        observation = ExperienceObservation(
            team_id=team_id,
            user_id=user_id,
            session_id=f"session-{index:02d}",
            observation=f"Use deployment canary value {index:02d}.",
        )
        policy_result = ExperiencePolicyResult(
            proposal=MemoryActionProposal(
                action="remember",
                kind="preference",
                key="deployment_canary_default",
                value=f"candidate-{index:02d}",
                confidence=1.0,
                importance=5,
                rationale="Concurrent Tablestore local-transaction proof.",
            ),
            provider_name="cloud-proof",
            model_name="deterministic-contract",
        )
        barrier.wait()
        result = service.apply_policy_result(observation, policy_result)
        memory_id = result.memory.memory_id if result.memory else None
        return result.decision.action, memory_id

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(write, range(concurrency)))
    duration = round(time.monotonic() - started, 3)
    memories = repository.list_memories(
        team_id=team_id,
        user_id=user_id,
        include_inactive=True,
    )
    decisions = repository.list_decisions(team_id=team_id, user_id=user_id)
    active = [memory for memory in memories if memory.status == "active"]
    superseded = [memory for memory in memories if memory.status == "superseded"]
    if len(results) != concurrency:
        raise RuntimeError("Not every concurrent Tablestore request completed.")
    if len(active) != 1 or len(superseded) != concurrency - 1:
        raise RuntimeError("Concurrent writes violated the one-active-truth invariant.")
    if len(memories) != concurrency or len(decisions) != concurrency:
        raise RuntimeError("Concurrent writes lost memory history or decision receipts.")
    if any(memory.superseded_by is None for memory in superseded):
        raise RuntimeError("A superseded memory is missing its successor link.")
    return {
        "scope": {"teamId": team_id, "userId": user_id},
        "requestsAttempted": concurrency,
        "requestsSucceeded": len(results),
        "rememberActions": sum(action == "remember" for action, _ in results),
        "supersedeActions": sum(action == "supersede" for action, _ in results),
        "memoryCount": len(memories),
        "activeCount": len(active),
        "supersededCount": len(superseded),
        "decisionCount": len(decisions),
        "winningMemoryId": active[0].memory_id,
        "winningValue": active[0].value,
        "transactionStartAttempts": (
            client.transaction_start_attempts - attempts_before
        ),
        "transactionStartConflictsRetried": (
            client.transaction_start_conflicts - conflicts_before
        ),
        "durationSeconds": duration,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate sanitized real-cloud Tablestore durability evidence."
    )
    parser.add_argument("--env-file", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--instance", default="")
    parser.add_argument("--table", default="")
    parser.add_argument("--concurrency", type=int, default=20, choices=range(2, 51))
    parser.add_argument(
        "--output-dir",
        default="artifacts/qwencloud-proof/tablestore",
    )
    return parser.parse_args()


def _load_settings(env_file: str) -> dict[str, str | None]:
    if not env_file:
        return {}
    path = Path(env_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
    return dict(dotenv_values(path))


def _setting(settings: dict[str, str | None], name: str) -> str | None:
    value = os.getenv(name) or settings.get(name)
    return value.strip() if value and value.strip() else None


def _required_setting(settings: dict[str, str | None], name: str) -> str:
    value = _setting(settings, name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Tablestore proof failed: {exc}", file=sys.stderr)
        raise
