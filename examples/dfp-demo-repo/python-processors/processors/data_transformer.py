# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations


class DataTransformer:
    def normalize_rows(
        self, rows: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        return [{str(key).lower(): value for key, value in row.items()} for row in rows]
