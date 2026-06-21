# SPDX-License-Identifier: Apache-2.0

import sqlite3
from pathlib import Path

from dream.core.errors import NotFoundError
from dream.core.paths import DEFAULT_DB_PATH
from dream.requirement_cases.models import RequirementCaseSnapshot


class RequirementCaseRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save(self, snapshot: RequirementCaseSnapshot) -> None:
        case = snapshot.case
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO requirement_cases (
                    case_id, team_id, title, raw_request, created_by_role,
                    target_app, target_component, status, created_at, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    case.team_id,
                    case.title,
                    case.raw_request,
                    case.created_by_role,
                    case.target_app,
                    case.target_component,
                    case.status,
                    case.created_at,
                    case.updated_at,
                    snapshot.model_dump_json(),
                ),
            )

    def get(self, case_id: str) -> RequirementCaseSnapshot:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM requirement_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Requirement case not found: {case_id}")
        return RequirementCaseSnapshot.model_validate_json(row["payload"])

    def list(self) -> list[RequirementCaseSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM requirement_cases
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [RequirementCaseSnapshot.model_validate_json(row["payload"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requirement_cases (
                    case_id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    raw_request TEXT NOT NULL,
                    created_by_role TEXT,
                    target_app TEXT,
                    target_component TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
