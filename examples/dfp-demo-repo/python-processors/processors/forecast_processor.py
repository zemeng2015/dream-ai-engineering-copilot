# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations


class ForecastProcessor:
    def run_forecast(
        self,
        execution_id: str,
        task_id: str,
        rows: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "executionId": execution_id,
            "taskId": task_id,
            "rowCount": len(rows),
            "status": "COMPLETED",
        }
