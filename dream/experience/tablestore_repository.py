# SPDX-License-Identifier: Apache-2.0

import hashlib
import os
import random
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from typing import Any

from dream.core.errors import DreamError, NotFoundError
from dream.experience.models import ExperienceDecisionRecord, ExperienceMemory
from dream.experience.repository import ExperienceMemoryStore

DEFAULT_TABLE_NAME = "dream_experience_v1"
DEFAULT_TRANSACTION_ATTEMPTS = 12
PAGE_SIZE = 100


class _TablestoreExperienceMemoryStore:
    def __init__(
        self,
        *,
        client: Any,
        table_name: str,
        transaction_id: str | None = None,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        self.client = client
        self.table_name = table_name
        self.transaction_id = transaction_id
        self.team_id = team_id
        self.user_id = user_id

    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory:
        self._assert_scope(memory.team_id, memory.user_id)
        self._put_payload(
            team_id=memory.team_id,
            user_id=memory.user_id,
            record_id=f"m#{memory.memory_id}",
            record_type="memory",
            status=memory.status,
            updated_at=memory.updated_at,
            payload=memory.model_dump_json(),
        )
        return memory

    def get_memory(
        self,
        memory_id: str,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> ExperienceMemory:
        resolved_team, resolved_user = self._resolve_scope(team_id, user_id)
        _, row, _ = self.client.get_row(
            self.table_name,
            _primary_key(resolved_team, resolved_user, f"m#{memory_id}"),
            columns_to_get=["payload"],
            transaction_id=self.transaction_id,
        )
        if row is None:
            raise NotFoundError(f"Experience memory not found: {memory_id}")
        payload = _attribute_value(row, "payload")
        if payload is None:
            raise DreamError(f"Tablestore memory row has no payload: {memory_id}")
        return ExperienceMemory.model_validate_json(payload)

    def list_memories(
        self,
        *,
        team_id: str,
        user_id: str,
        include_inactive: bool = True,
    ) -> list[ExperienceMemory]:
        self._assert_scope(team_id, user_id)
        memories = [
            ExperienceMemory.model_validate_json(payload)
            for record_id, payload in self._list_payloads(team_id, user_id)
            if record_id.startswith("m#")
        ]
        if not include_inactive:
            memories = [memory for memory in memories if memory.status == "active"]
        memories.sort(key=lambda memory: memory.memory_id)
        memories.sort(key=lambda memory: memory.updated_at, reverse=True)
        return memories

    def append_decision(
        self,
        decision: ExperienceDecisionRecord,
    ) -> ExperienceDecisionRecord:
        self._assert_scope(decision.team_id, decision.user_id)
        self._put_payload(
            team_id=decision.team_id,
            user_id=decision.user_id,
            record_id=f"d#{decision.decision_id}",
            record_type="decision",
            status=decision.action,
            updated_at=decision.created_at,
            payload=decision.model_dump_json(),
        )
        return decision

    def list_decisions(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> list[ExperienceDecisionRecord]:
        self._assert_scope(team_id, user_id)
        decisions = [
            ExperienceDecisionRecord.model_validate_json(payload)
            for record_id, payload in self._list_payloads(team_id, user_id)
            if record_id.startswith("d#")
        ]
        return sorted(decisions, key=lambda decision: (decision.created_at, decision.decision_id))

    def _put_payload(
        self,
        *,
        team_id: str,
        user_id: str,
        record_id: str,
        record_type: str,
        status: str,
        updated_at: str,
        payload: str,
    ) -> None:
        sdk = _tablestore_sdk()
        row = sdk.Row(
            _primary_key(team_id, user_id, record_id),
            [
                ("record_type", record_type),
                ("status", status),
                ("updated_at", updated_at),
                ("payload", payload),
            ],
        )
        condition = sdk.Condition(sdk.RowExistenceExpectation.IGNORE)
        self.client.put_row(
            self.table_name,
            row,
            condition,
            transaction_id=self.transaction_id,
        )

    def _list_payloads(self, team_id: str, user_id: str) -> list[tuple[str, str]]:
        sdk = _tablestore_sdk()
        scope_id = _scope_id(team_id, user_id)
        start = [("scope_id", scope_id), ("record_id", sdk.INF_MIN)]
        end = [("scope_id", scope_id), ("record_id", sdk.INF_MAX)]
        payloads: list[tuple[str, str]] = []
        while True:
            _, next_start, rows, next_token = self.client.get_range(
                self.table_name,
                "FORWARD",
                start,
                end,
                columns_to_get=["payload"],
                limit=PAGE_SIZE,
                transaction_id=self.transaction_id,
            )
            for row in rows:
                record_id = _primary_key_value(row, "record_id")
                payload = _attribute_value(row, "payload")
                if isinstance(record_id, str) and isinstance(payload, str):
                    payloads.append((record_id, payload))
            if next_token:
                raise DreamError("Unexpected wide-row continuation from Tablestore.")
            if not next_start:
                break
            start = next_start
        return payloads

    def _resolve_scope(
        self,
        team_id: str | None,
        user_id: str | None,
    ) -> tuple[str, str]:
        if team_id is None and user_id is None:
            if self.team_id is None or self.user_id is None:
                raise DreamError(
                    "Tablestore memory lookups require both team_id and user_id."
                )
            return self.team_id, self.user_id
        if team_id is None or user_id is None:
            raise DreamError("Both team_id and user_id are required for a memory lookup.")
        self._assert_scope(team_id, user_id)
        return team_id, user_id

    def _assert_scope(self, team_id: str, user_id: str) -> None:
        if self.team_id is None and self.user_id is None:
            return
        if team_id != self.team_id or user_id != self.user_id:
            raise DreamError("Tablestore transaction cannot cross its user partition.")


class TablestoreExperienceMemoryRepository:
    backend_name = "tablestore"
    durable = True

    def __init__(
        self,
        *,
        client: Any,
        table_name: str = DEFAULT_TABLE_NAME,
        transaction_attempts: int = DEFAULT_TRANSACTION_ATTEMPTS,
    ) -> None:
        if not table_name.strip():
            raise DreamError("Tablestore table name cannot be empty.")
        if transaction_attempts < 1:
            raise DreamError("Tablestore transaction attempts must be at least 1.")
        self.client = client
        self.table_name = table_name.strip()
        self.transaction_attempts = transaction_attempts

    @classmethod
    def from_env(cls) -> "TablestoreExperienceMemoryRepository":
        sdk = _tablestore_sdk()
        endpoint = _required_env("ALIBABA_TABLESTORE_ENDPOINT")
        instance_name = _required_env("ALIBABA_TABLESTORE_INSTANCE")
        access_key_id = _required_env(
            "ALIBABA_CLOUD_ACCESS_KEY_ID",
            "ALIBABA_TABLESTORE_ACCESS_KEY_ID",
        )
        access_key_secret = _required_env(
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
            "ALIBABA_TABLESTORE_ACCESS_KEY_SECRET",
        )
        sts_token = _optional_env(
            "ALIBABA_CLOUD_SECURITY_TOKEN",
            "ALIBABA_TABLESTORE_SECURITY_TOKEN",
        )
        region = os.getenv("ALIBABA_CLOUD_REGION", "ap-southeast-1").strip()
        client = sdk.OTSClient(
            endpoint,
            access_key_id,
            access_key_secret,
            instance_name,
            sts_token=sts_token,
            region=region or None,
            enable_native=False,
        )
        attempts = _positive_int_env(
            "DREAM_TABLESTORE_TRANSACTION_ATTEMPTS",
            DEFAULT_TRANSACTION_ATTEMPTS,
        )
        return cls(
            client=client,
            table_name=os.getenv("ALIBABA_TABLESTORE_TABLE", DEFAULT_TABLE_NAME),
            transaction_attempts=attempts,
        )

    def save_memory(self, memory: ExperienceMemory) -> ExperienceMemory:
        return self._store().save_memory(memory)

    def get_memory(
        self,
        memory_id: str,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> ExperienceMemory:
        return self._store().get_memory(
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
        return self._store().list_memories(
            team_id=team_id,
            user_id=user_id,
            include_inactive=include_inactive,
        )

    def append_decision(
        self,
        decision: ExperienceDecisionRecord,
    ) -> ExperienceDecisionRecord:
        return self._store().append_decision(decision)

    def list_decisions(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> list[ExperienceDecisionRecord]:
        return self._store().list_decisions(team_id=team_id, user_id=user_id)

    @contextmanager
    def transaction(
        self,
        *,
        team_id: str,
        user_id: str,
    ) -> Iterator[ExperienceMemoryStore]:
        transaction_id = self._start_transaction(team_id, user_id)
        try:
            yield self._store(
                transaction_id=transaction_id,
                team_id=team_id,
                user_id=user_id,
            )
        except Exception:
            self._abort_quietly(transaction_id)
            raise
        else:
            try:
                self.client.commit_transaction(transaction_id)
            except Exception:
                self._abort_quietly(transaction_id)
                raise

    def _store(
        self,
        *,
        transaction_id: str | None = None,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> _TablestoreExperienceMemoryStore:
        return _TablestoreExperienceMemoryStore(
            client=self.client,
            table_name=self.table_name,
            transaction_id=transaction_id,
            team_id=team_id,
            user_id=user_id,
        )

    def _start_transaction(self, team_id: str, user_id: str) -> str:
        key = [("scope_id", _scope_id(team_id, user_id))]
        for attempt in range(self.transaction_attempts):
            try:
                return self.client.start_local_transaction(self.table_name, key)
            except Exception as exc:
                if attempt + 1 >= self.transaction_attempts or not _is_lock_conflict(exc):
                    raise
                ceiling = min(0.5, 0.025 * (2**attempt))
                time.sleep(random.uniform(ceiling / 2, ceiling))
        raise AssertionError("Unreachable transaction retry state.")

    def _abort_quietly(self, transaction_id: str) -> None:
        try:
            self.client.abort_transaction(transaction_id)
        except Exception:
            pass


def _scope_id(team_id: str, user_id: str) -> str:
    digest = hashlib.sha256(f"{team_id}\0{user_id}".encode()).hexdigest()
    return f"scope-{digest}"


def _primary_key(team_id: str, user_id: str, record_id: str) -> list[tuple[str, str]]:
    return [("scope_id", _scope_id(team_id, user_id)), ("record_id", record_id)]


def _primary_key_value(row: Any, name: str) -> Any:
    for column in row.primary_key or []:
        if column[0] == name:
            return column[1]
    return None


def _attribute_value(row: Any, name: str) -> Any:
    for column in row.attribute_columns or []:
        if column[0] == name:
            return column[1]
    return None


def _tablestore_sdk() -> Any:
    try:
        return import_module("tablestore")
    except ImportError as exc:
        raise DreamError(
            "The tablestore package is required when DREAM_EXPERIENCE_STORE=tablestore."
        ) from exc


def _required_env(*names: str) -> str:
    value = _optional_env(*names)
    if value is None:
        raise DreamError(f"Missing required environment variable: {' or '.join(names)}")
    return value


def _optional_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise DreamError(f"{name} must be a positive integer.") from exc
    if value < 1:
        raise DreamError(f"{name} must be a positive integer.")
    return value


def _is_lock_conflict(exc: Exception) -> bool:
    code = str(getattr(exc, "code", ""))
    return "conflict" in code.lower() or "transaction" in code.lower()
