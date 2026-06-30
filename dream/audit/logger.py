# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dream.audit.models import AuditRecord
from dream.audit.repository import AuditRepository


class AuditLogger:
    def __init__(
        self,
        repository: AuditRepository | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.repository = repository or AuditRepository(db_path=db_path)

    def log_generation(
        self,
        *,
        run_id: str,
        use_case: str,
        team_id: str,
        case_id: str | None = None,
        repo_name: str | None = None,
        input_payload: dict[str, Any],
        retrieved_source_paths: list[str],
        model_provider: str,
        model_name: str,
        output_path: str,
        status: str,
        warnings: list[str],
    ) -> AuditRecord:
        record = AuditRecord(
            run_id=run_id,
            timestamp=datetime.now(UTC).isoformat(),
            use_case=use_case,
            team_id=team_id,
            case_id=case_id,
            repo_name=repo_name,
            input_hash=self.hash_input(input_payload),
            retrieved_source_paths=retrieved_source_paths,
            model_provider=model_provider,
            model_name=model_name,
            output_path=output_path,
            status=status,
            warnings=warnings,
        )
        self.repository.add_audit_record(record)
        return record

    @staticmethod
    def hash_input(input_payload: dict[str, Any]) -> str:
        normalized = json.dumps(input_payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
