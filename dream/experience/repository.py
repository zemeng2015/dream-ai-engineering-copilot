# SPDX-License-Identifier: Apache-2.0

import os
import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Protocol

from dream.core.errors import DreamError, NotFoundError
from dream.core.paths import ensure_artifacts_dir
from dream.experience.models import ExperienceDecisionRecord, ExperienceMemory


class ExperienceMemoryStore(Protocol):
    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory: ...

    def get_memory(
        self,
        memory_id: str,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> ExperienceMemory: ...

    def list_memories(
        self,
        *,
        team_id: str,
        user_id: str,
        include_inactive: bool = True,
    ) -> list[ExperienceMemory]: ...

    def append_decision(
        self, decision: ExperienceDecisionRecord
    ) -> ExperienceDecisionRecord: ...

    def list_decisions(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> list[ExperienceDecisionRecord]: ...


class ExperienceMemoryRepositoryProtocol(ExperienceMemoryStore, Protocol):
    backend_name: str
    durable: bool

    def transaction(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> AbstractContextManager[ExperienceMemoryStore]: ...


class _SQLiteExperienceMemoryStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory:
        self.conn.execute(
            """
            INSERT INTO experience_memories (
                memory_id, team_id, user_id, status, memory_kind, memory_key,
                updated_at, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                team_id = excluded.team_id,
                user_id = excluded.user_id,
                status = excluded.status,
                memory_kind = excluded.memory_kind,
                memory_key = excluded.memory_key,
                updated_at = excluded.updated_at,
                payload = excluded.payload
            """,
            (
                memory.memory_id,
                memory.team_id,
                memory.user_id,
                memory.status,
                memory.kind,
                memory.key,
                memory.updated_at,
                memory.model_dump_json(),
            ),
        )
        return memory

    def get_memory(
        self,
        memory_id: str,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> ExperienceMemory:
        _validate_optional_scope(team_id, user_id)
        query = "SELECT payload FROM experience_memories WHERE memory_id = ?"
        params: list[str] = [memory_id]
        if team_id is not None and user_id is not None:
            query += " AND team_id = ? AND user_id = ?"
            params.extend([team_id, user_id])
        row = self.conn.execute(query, params).fetchone()
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
        rows = self.conn.execute(query, params).fetchall()
        return [ExperienceMemory.model_validate_json(row["payload"]) for row in rows]

    def append_decision(
        self, decision: ExperienceDecisionRecord
    ) -> ExperienceDecisionRecord:
        self.conn.execute(
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
        rows = self.conn.execute(
            """
            SELECT payload FROM experience_decisions
            WHERE team_id = ? AND user_id = ?
            ORDER BY created_at, decision_id
            """,
            (team_id, user_id),
        ).fetchall()
        return [ExperienceDecisionRecord.model_validate_json(row["payload"]) for row in rows]


class ExperienceMemoryRepository:
    backend_name = "sqlite"
    durable = False

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self._default_db_path()
        self.db_path = self.db_path.expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory:
        with self._connect() as conn:
            return _SQLiteExperienceMemoryStore(conn).save_memory(memory)

    def get_memory(
        self,
        memory_id: str,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> ExperienceMemory:
        with self._connect() as conn:
            return _SQLiteExperienceMemoryStore(conn).get_memory(
                memory_id,
                team_id=team_id,
                user_id=user_id,
            )

    def list_memories(
        self,
        *,
        team_id: str,
        user_id: str,
        include_inactive: bool = True,
    ) -> list[ExperienceMemory]:
        with self._connect() as conn:
            return _SQLiteExperienceMemoryStore(conn).list_memories(
                team_id=team_id,
                user_id=user_id,
                include_inactive=include_inactive,
            )

    def append_decision(
        self, decision: ExperienceDecisionRecord
    ) -> ExperienceDecisionRecord:
        with self._connect() as conn:
            return _SQLiteExperienceMemoryStore(conn).append_decision(decision)

    def list_decisions(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> list[ExperienceDecisionRecord]:
        with self._connect() as conn:
            return _SQLiteExperienceMemoryStore(conn).list_decisions(
                team_id=team_id,
                user_id=user_id,
            )

    @contextmanager
    def transaction(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> Iterator[ExperienceMemoryStore]:
        del team_id, user_id
        with self._connect(begin_immediate=True) as conn:
            yield _SQLiteExperienceMemoryStore(conn)

    @contextmanager
    def _connect(self, *, begin_immediate: bool = False) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            if begin_immediate:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect(begin_immediate=True) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experience_memories (
                    memory_id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    memory_kind TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(experience_memories)").fetchall()
            }
            if "memory_kind" not in columns:
                conn.execute(
                    "ALTER TABLE experience_memories "
                    "ADD COLUMN memory_kind TEXT NOT NULL DEFAULT ''"
                )
                rows = conn.execute(
                    "SELECT memory_id, payload FROM experience_memories"
                ).fetchall()
                for row in rows:
                    memory = ExperienceMemory.model_validate_json(row["payload"])
                    conn.execute(
                        "UPDATE experience_memories SET memory_kind = ? WHERE memory_id = ?",
                        (memory.kind, row["memory_id"]),
                    )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experience_memory_scope
                ON experience_memories(team_id, user_id, status, updated_at)
                """
            )
            self._repair_duplicate_active_keys(conn)
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_experience_one_active_truth
                ON experience_memories(team_id, user_id, memory_kind, memory_key)
                WHERE status = 'active'
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
    def _repair_duplicate_active_keys(conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT payload FROM experience_memories
            WHERE status = 'active'
            ORDER BY updated_at DESC, memory_id DESC
            """
        ).fetchall()
        active: dict[tuple[str, str, str, str], ExperienceMemory] = {}
        store = _SQLiteExperienceMemoryStore(conn)
        for row in rows:
            memory = ExperienceMemory.model_validate_json(row["payload"])
            scope = (memory.team_id, memory.user_id, memory.kind, memory.key)
            current = active.get(scope)
            if current is None:
                active[scope] = memory
                continue
            store.save_memory(
                memory.model_copy(
                    update={
                        "status": "superseded",
                        "superseded_by": current.memory_id,
                        "updated_at": current.updated_at,
                    }
                )
            )

    @staticmethod
    def _default_db_path() -> Path:
        configured = os.getenv("DREAM_EXPERIENCE_DB_PATH", "").strip()
        if configured:
            return Path(configured)
        return ensure_artifacts_dir() / "experience-memory.sqlite"


def create_experience_memory_repository() -> ExperienceMemoryRepositoryProtocol:
    backend = os.getenv("DREAM_EXPERIENCE_STORE", "sqlite").strip().lower()
    if backend == "sqlite":
        return ExperienceMemoryRepository()
    if backend == "tablestore":
        from dream.experience.tablestore_repository import (
            TablestoreExperienceMemoryRepository,
        )

        return TablestoreExperienceMemoryRepository.from_env()
    raise DreamError(
        "Unsupported DREAM_EXPERIENCE_STORE. Expected 'sqlite' or 'tablestore'."
    )


def _validate_optional_scope(team_id: str | None, user_id: str | None) -> None:
    if (team_id is None) != (user_id is None):
        raise DreamError("Both team_id and user_id are required when scoping a memory lookup.")
