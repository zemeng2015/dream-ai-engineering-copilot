from __future__ import annotations


def handle_service_task(
    event: dict[str, object], context: object | None = None
) -> dict[str, object]:
    execution_id = str(event.get("executionId", "missing-execution"))
    task_id = str(event.get("taskId", "service-task"))
    return {
        "executionId": execution_id,
        "taskId": task_id,
        "status": "COMPLETED",
        "context": str(context),
    }
