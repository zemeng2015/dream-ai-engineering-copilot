import sys
from pathlib import Path

PROCESSOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROCESSOR_ROOT))

from processors.output_aggregator import OutputAggregator  # noqa: E402


def test_manifest_contains_stable_idempotency_key() -> None:
    manifest = OutputAggregator().build_manifest("exec-1", "task-1", "attempt-1", 10)
    assert manifest["idempotencyKey"] == "exec-1:task-1:attempt-1"
    assert manifest["storageKey"] == "dfp-demo/exec-1/task-1/result.csv"
