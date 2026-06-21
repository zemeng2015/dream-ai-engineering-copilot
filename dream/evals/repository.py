# SPDX-License-Identifier: Apache-2.0

import sqlite3
from pathlib import Path

from dream.core.paths import DEFAULT_DB_PATH
from dream.evals.models import EvaluationScorecard


class EvaluationRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save(self, scorecard: EvaluationScorecard) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evaluation_scorecards (
                    evaluation_id, created_at, target_type, target_id, run_id, case_id,
                    team_id, repo_name, overall_score, grade, pass_status,
                    evaluated_artifact_path, output_path, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scorecard.evaluation_id,
                    scorecard.created_at,
                    scorecard.target_type,
                    scorecard.target_id,
                    scorecard.run_id,
                    scorecard.case_id,
                    scorecard.team_id,
                    scorecard.repo_name,
                    scorecard.overall_score,
                    scorecard.grade,
                    scorecard.pass_status,
                    scorecard.evaluated_artifact_path,
                    scorecard.output_path,
                    scorecard.model_dump_json(),
                ),
            )

    def get(self, evaluation_id: str) -> EvaluationScorecard | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM evaluation_scorecards WHERE evaluation_id = ?",
                (evaluation_id,),
            ).fetchone()
        return EvaluationScorecard.model_validate_json(row["payload"]) if row else None

    def list(self) -> list[EvaluationScorecard]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM evaluation_scorecards
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [EvaluationScorecard.model_validate_json(row["payload"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_scorecards (
                    evaluation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT,
                    run_id TEXT,
                    case_id TEXT,
                    team_id TEXT,
                    repo_name TEXT,
                    overall_score REAL NOT NULL,
                    grade TEXT NOT NULL,
                    pass_status TEXT NOT NULL,
                    evaluated_artifact_path TEXT,
                    output_path TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
