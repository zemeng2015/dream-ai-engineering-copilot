# SPDX-License-Identifier: Apache-2.0

import os
import sqlite3
from pathlib import Path

from dream.core.errors import NotFoundError
from dream.core.paths import ensure_artifacts_dir
from dream.experience.models import ExperienceDecisionRecord, ExperienceMemory


class ExperienceMemoryRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self._default_db_path()
        self.db_path = self.db_path.expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experience_memories (
                    memory_id, team_id, user_id, status, memory_key, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    team_id = excluded.team_id,
                    user_id = excluded.user_id,
                    status = excluded.status,
                    memory_key = excluded.memory_key,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    memory.memory_id,
                    memory.team_id,
                    memory.user_id,
                    memory.status,
                    memory.key,
                    memory.updated_at,
                    memory.model_dump_json(),
                ),
            )
        return memory

    def get_memory(self, memory_id: str) -> ExperienceMemory:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM experience_memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Experience memory not found: {memory_id}")
        return ExperienceMemory.model_validate_json(row["payload"])

    def list_memories(
        self,
        *,
        team_id: str,
        user_id: str,
        include_inactive: bool = True,
    ) -> list[ExperienceMemory]:
        query = (
            "SELECT payload FROM experience_memories "
            "WHERE team_id = ? AND user_id = ?"
        )
        params: list[str] = [team_id, user_id]
        if not include_inactive:
            query += " AND status = ?"
            params.append("active")
        query += " ORDER BY updated_at DESC, memory_id"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [ExperienceMemory.model_validate_json(row["payload"]) for row in rows]

    def append_decision(self, decision: ExperienceDecisionRecord) -> ExperienceDecisionRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experience_decisions (
                    decision_id, team_id, user_id, session_id, created_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.team_id,
                    decision.user_id,
                    decision.session_id,
                    decision.created_at,
                    decision.model_dump_json(),
                ),
            )
        return decision

    def list_decisions(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> list[ExperienceDecisionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM experience_decisions
                WHERE team_id = ? AND user_id = ?
                ORDER BY created_at, decision_id
                """,
                (team_id, user_id),
            ).fetchall()
        return [ExperienceDecisionRecord.model_validate_json(row["payload"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experience_memories (
                    memory_id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experience_memory_scope
                ON experience_memories(team_id, user_id, status, updated_at)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experience_decisions (
                    decision_id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experience_decision_scope
                ON experience_decisions(team_id, user_id, created_at)
                """
            )

    @staticmethod
    def _default_db_path() -> Path:
        configured = os.getenv("DREAM_EXPERIENCE_DB_PATH", "").strip()
        if configured:
            return Path(configured)
        return ensure_artifacts_dir() / "experience-memory.sqlite"

