from __future__ import annotations


def run_batch_task(execution_id: str, task_id: str, attempt_count: int) -> dict[str, object]:
    if attempt_count > 3:
        return {"executionId": execution_id, "taskId": task_id, "status": "FAILED"}
    return {"executionId": execution_id, "taskId": task_id, "status": "COMPLETED"}
