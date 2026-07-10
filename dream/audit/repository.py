# SPDX-License-Identifier: Apache-2.0

import json
import sqlite3
from pathlib import Path

from dream.audit.models import AuditRecord
from dream.core.paths import get_audit_db_path
from dream.evals.models import HumanRating


class AuditRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_audit_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def add_audit_record(self, record: AuditRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_runs (
                    run_id, timestamp, use_case, team_id, case_id, repo_name, input_hash,
                    retrieved_source_paths, model_provider, model_name,
                    output_path, status, warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.timestamp,
                    record.use_case,
                    record.team_id,
                    record.case_id,
                    record.repo_name,
                    record.input_hash,
                    json.dumps(record.retrieved_source_paths),
                    record.model_provider,
                    record.model_name,
                    record.output_path,
                    record.status,
                    json.dumps(record.warnings),
                ),
            )

    def list_audit_records(self) -> list[AuditRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, timestamp, use_case, team_id, case_id, repo_name,
                       input_hash, retrieved_source_paths, model_provider, model_name,
                       output_path, status, warnings
                FROM audit_runs
                ORDER BY timestamp DESC
                """
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def get_audit_record(self, run_id: str) -> AuditRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, timestamp, use_case, team_id, case_id, repo_name,
                       input_hash, retrieved_source_paths, model_provider, model_name,
                       output_path, status, warnings
                FROM audit_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._record_from_row(row) if row else None

    def add_rating(self, rating: HumanRating) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO human_ratings (
                    run_id, usefulness_score, correctness_score, comments, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rating.run_id,
                    rating.usefulness_score,
                    rating.correctness_score,
                    rating.comments,
                    rating.created_at,
                ),
            )

    def list_ratings(self, run_id: str) -> list[HumanRating]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, usefulness_score, correctness_score, comments, created_at
                FROM human_ratings
                WHERE run_id = ?
                ORDER BY created_at DESC
                """,
                (run_id,),
            ).fetchall()
        return [
            HumanRating(
                run_id=row["run_id"],
                usefulness_score=row["usefulness_score"],
                correctness_score=row["correctness_score"],
                comments=row["comments"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def delete_case_records(self, case_id: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id FROM audit_runs WHERE case_id = ?",
                (case_id,),
            ).fetchall()
            run_ids = [row["run_id"] for row in rows]
            if run_ids:
                placeholders = ",".join("?" for _ in run_ids)
                conn.execute(
                    f"DELETE FROM human_ratings WHERE run_id IN ({placeholders})",
                    run_ids,
                )
            conn.execute("DELETE FROM audit_runs WHERE case_id = ?", (case_id,))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    use_case TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    case_id TEXT,
                    repo_name TEXT,
                    input_hash TEXT NOT NULL,
                    retrieved_source_paths TEXT NOT NULL,
                    model_provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    warnings TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "audit_runs", "case_id", "TEXT")
            self._ensure_column(conn, "audit_runs", "repo_name", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS human_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    usefulness_score INTEGER NOT NULL,
                    correctness_score INTEGER NOT NULL,
                    comments TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            run_id=row["run_id"],
            timestamp=row["timestamp"],
            use_case=row["use_case"],
            team_id=row["team_id"],
            case_id=row["case_id"],
            repo_name=row["repo_name"],
            input_hash=row["input_hash"],
            retrieved_source_paths=json.loads(row["retrieved_source_paths"]),
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            output_path=row["output_path"],
            status=row["status"],
            warnings=json.loads(row["warnings"]),
        )

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str
    ) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {row["name"] for row in rows}
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
