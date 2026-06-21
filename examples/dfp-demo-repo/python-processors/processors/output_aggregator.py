from __future__ import annotations

import hashlib


class OutputAggregator:
    def build_manifest(
        self, execution_id: str, task_id: str, attempt_id: str, row_count: int
    ) -> dict[str, object]:
        idempotency_key = f"{execution_id}:{task_id}:{attempt_id}"
        checksum = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:12]
        return {
            "executionId": execution_id,
            "taskId": task_id,
            "attemptId": attempt_id,
            "idempotencyKey": idempotency_key,
            "checksum": checksum,
            "rowCount": row_count,
            "storageKey": f"dfp-demo/{execution_id}/{task_id}/result.csv",
        }
