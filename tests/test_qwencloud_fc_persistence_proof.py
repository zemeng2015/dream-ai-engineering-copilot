# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud_fc_persistence_proof.py"
BUILD_SHA = "a" * 40
MEMORY_ID = "experience-memory-proof123"
DECISION_ID = "experience-decision-proof123"
RECEIPT = {
    "schema_version": "llm-receipt-v1",
    "endpoint_host": "dashscope-intl.aliyuncs.com",
    "request_sha256": "b" * 64,
    "response_sha256": "c" * 64,
    "requested_at": "2026-07-12T12:00:00+00:00",
    "completed_at": "2026-07-12T12:00:01+00:00",
    "latency_ms": 1000,
    "provider_request_id": "provider-request-proof",
    "response_id": "response-proof",
}


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qwencloud_fc_persistence_proof", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _health(module: ModuleType, instance_id: str):
    return module.HttpResult(
        status=200,
        body={
            "deployment_target": "Alibaba Cloud Function Compute custom runtime",
            "alibaba_cloud_region": "ap-southeast-1",
            "alibaba_cloud_service": "Function Compute custom runtime",
            "llm_provider": "qwen-cloud",
            "llm_model": "qwen3.7-plus",
            "llm_api_key_configured": True,
            "experience_storage_backend": "tablestore",
            "experience_storage_durable": True,
            "experience_transaction_mode": "partition-local-transaction",
            "runtime_instance_id": instance_id,
            "build_sha": BUILD_SHA,
        },
        headers={
            "x-dream-build-sha": BUILD_SHA,
            "x-dream-fc-instance-id": instance_id,
        },
        latency_ms=20,
    )


def _capture(module: ModuleType):
    return module.HttpResult(
        status=200,
        body={
            "decision": {
                "decision_id": DECISION_ID,
                "action": "remember",
                "created_memory_id": MEMORY_ID,
                "provider_name": "qwen-cloud",
                "model_name": "qwen3.7-plus",
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 40},
                "llm_receipt": RECEIPT,
            },
            "memory": {
                "memory_id": MEMORY_ID,
                "key": "production_traffic_migration_order",
                "value": "run and verify database migrations first",
                "status": "active",
            },
        },
        headers={"x-dream-fc-instance-id": "instance-a"},
        latency_ms=1200,
    )


def _memory() -> dict:
    return {
        "memory_id": MEMORY_ID,
        "key": "production_traffic_migration_order",
        "value": "run and verify database migrations first",
        "status": "active",
    }


def _decision() -> dict:
    return {
        "decision_id": DECISION_ID,
        "provider_name": "qwen-cloud",
        "model_name": "qwen3.7-plus",
        "llm_receipt": RECEIPT,
    }


def _recall(module: ModuleType, instance_id: str):
    return module.HttpResult(
        status=200,
        body={
            "selected": [{"memory": _memory()}],
            "estimated_tokens_used": 24,
        },
        headers={"x-dream-fc-instance-id": instance_id},
        latency_ms=30,
    )


def test_seed_and_verify_require_a_new_instance_and_preserve_qwen_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    current_instance = "instance-a"

    def fake_request(base_url, path, *, method="GET", payload=None, timeout=120.0):
        del base_url, payload, timeout
        if path == "/health":
            return _health(module, current_instance)
        if path == "/experience/capture" and method == "POST":
            return _capture(module)
        if path == "/experience/recall" and method == "POST":
            return _recall(module, current_instance)
        if path.startswith("/experience/decisions?"):
            return module.HttpResult(200, [_decision()], {}, 10)
        if path.startswith("/experience/memories?"):
            return module.HttpResult(200, [_memory()], {}, 10)
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "_request_json", fake_request)
    state_path = tmp_path / "seed.json"
    state = module.seed(
        base_url="https://example.fcapp.run",
        expected_build=BUILD_SHA,
        state_file=state_path,
    )
    assert state["capture"]["provider"] == "qwen-cloud"
    assert state["capture"]["llmReceipt"]["response_sha256"] == "c" * 64
    assert state_path.is_file()

    with pytest.raises(RuntimeError, match="instance ID did not change"):
        module.verify(
            base_url="https://example.fcapp.run",
            state_file=state_path,
            output_dir=tmp_path / "proof",
        )

    current_instance = "instance-b"
    proof, output_path = module.verify(
        base_url="https://example.fcapp.run",
        state_file=state_path,
        output_dir=tmp_path / "proof",
    )
    assert proof["status"] == "pass"
    assert proof["runtimeTransition"] == {
        "seedInstanceId": "instance-a",
        "verifyInstanceId": "instance-b",
        "instanceChanged": True,
    }
    assert proof["qwen"]["responseSha256"] == "c" * 64
    assert proof["persistence"]["memoryId"] == MEMORY_ID
    assert proof["credentials"]["valuesRecorded"] is False
    assert json.loads(output_path.read_text(encoding="utf-8")) == proof
