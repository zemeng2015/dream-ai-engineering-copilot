# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from dream.core.errors import DreamError, NotFoundError
from dream.experience.models import ExperienceDecisionRecord, ExperienceMemory
from dream.experience.tablestore_repository import (
    TablestoreExperienceMemoryRepository,
)


@dataclass(frozen=True)
class _DataCall:
    operation: str
    transaction_id: str | None


class _InMemoryTablestoreClient:
    def __init__(self, *, page_size: int = 2) -> None:
        self.page_size = page_size
        self.rows: dict[tuple[str, str], Any] = {}
        self.data_calls: list[_DataCall] = []
        self.started: list[tuple[str, list[tuple[str, Any]], str]] = []
        self.committed: list[str] = []
        self.aborted: list[str] = []
        self.paginated_responses = 0
        self._pending: dict[str, dict[tuple[str, str], Any]] = {}
        self._transaction_scopes: dict[str, str] = {}
        self.empty_next_token: bytes | None = None

    def put_row(
        self,
        table_name: str,
        row: Any,
        condition: Any = None,
        return_type: Any = None,
        transaction_id: str | None = None,
    ) -> tuple[None, None]:
        del condition, return_type
        primary_key = self._row_primary_key(row)
        key = self._storage_key(primary_key)
        self._payload(row)
        self.data_calls.append(_DataCall("put_row", transaction_id))
        if transaction_id is None:
            self.rows[key] = row
        else:
            self._check_transaction_scope(transaction_id, primary_key)
            self._pending[transaction_id][key] = row
        assert table_name
        return None, None

    def get_row(
        self,
        table_name: str,
        primary_key: Any,
        columns_to_get: Any = None,
        column_filter: Any = None,
        max_version: int = 1,
        time_range: Any = None,
        start_column: Any = None,
        end_column: Any = None,
        token: Any = None,
        transaction_id: str | None = None,
    ) -> tuple[None, Any | None, None]:
        del (
            columns_to_get,
            column_filter,
            max_version,
            time_range,
            start_column,
            end_column,
            token,
        )
        pairs = self._pairs(primary_key)
        self.data_calls.append(_DataCall("get_row", transaction_id))
        if transaction_id is not None:
            self._check_transaction_scope(transaction_id, pairs)
        assert table_name
        return None, self._visible_rows(transaction_id).get(self._storage_key(pairs)), None

    def get_range(
        self,
        table_name: str,
        direction: Any,
        inclusive_start_primary_key: Any,
        exclusive_end_primary_key: Any,
        columns_to_get: Any = None,
        limit: int | None = None,
        column_filter: Any = None,
        max_version: int = 1,
        time_range: Any = None,
        start_column: Any = None,
        end_column: Any = None,
        token: Any = None,
        transaction_id: str | None = None,
    ) -> tuple[None, list[tuple[str, Any]] | None, list[Any], None]:
        del (
            direction,
            columns_to_get,
            column_filter,
            max_version,
            time_range,
            start_column,
            end_column,
            token,
        )
        start = self._pairs(inclusive_start_primary_key)
        end = self._pairs(exclusive_end_primary_key)
        self.data_calls.append(_DataCall("get_range", transaction_id))
        assert table_name

        visible = self._visible_rows(transaction_id)
        matching = [
            row
            for row in visible.values()
            if self._rank_primary_key(start)
            <= self._rank_primary_key(self._row_primary_key(row))
            < self._rank_primary_key(end)
        ]
        matching.sort(key=lambda row: self._rank_primary_key(self._row_primary_key(row)))

        requested_size = limit if limit is not None else self.page_size
        page_size = min(self.page_size, requested_size)
        page = matching[:page_size]
        next_primary_key = None
        if len(matching) > page_size:
            next_primary_key = self._row_primary_key(matching[page_size])
            self.paginated_responses += 1
        return None, next_primary_key, page, self.empty_next_token

    def start_local_transaction(self, table_name: str, key: Any) -> str:
        partition_key = self._pairs(key)
        assert [name for name, _ in partition_key] == ["scope_id"]
        transaction_id = f"transaction-{len(self.started) + 1}"
        scope_id = str(partition_key[0][1])
        self.started.append((table_name, partition_key, transaction_id))
        self._transaction_scopes[transaction_id] = scope_id
        self._pending[transaction_id] = {}
        return transaction_id

    def commit_transaction(self, transaction_id: str) -> None:
        self.rows.update(self._pending.pop(transaction_id))
        self._transaction_scopes.pop(transaction_id)
        self.committed.append(transaction_id)

    def abort_transaction(self, transaction_id: str) -> None:
        self._pending.pop(transaction_id)
        self._transaction_scopes.pop(transaction_id)
        self.aborted.append(transaction_id)

    def stored_primary_keys(self) -> list[list[tuple[str, Any]]]:
        return [self._row_primary_key(row) for row in self.rows.values()]

    def stored_payloads(self) -> list[dict[str, Any]]:
        return [json.loads(self._payload(row)) for row in self.rows.values()]

    def _visible_rows(self, transaction_id: str | None) -> dict[tuple[str, str], Any]:
        visible = dict(self.rows)
        if transaction_id is not None:
            if transaction_id not in self._pending:
                raise AssertionError(f"Unknown transaction: {transaction_id}")
            visible.update(self._pending[transaction_id])
        return visible

    def _check_transaction_scope(
        self,
        transaction_id: str,
        primary_key: list[tuple[str, Any]],
    ) -> None:
        expected_scope = self._transaction_scopes.get(transaction_id)
        if expected_scope is None:
            raise AssertionError(f"Unknown transaction: {transaction_id}")
        actual_scope = str(dict(primary_key)["scope_id"])
        if actual_scope != expected_scope:
            raise AssertionError("SDK call crossed the local transaction partition")

    @classmethod
    def _storage_key(cls, primary_key: list[tuple[str, Any]]) -> tuple[str, str]:
        assert [name for name, _ in primary_key] == ["scope_id", "record_id"]
        return str(primary_key[0][1]), str(primary_key[1][1])

    @classmethod
    def _row_primary_key(cls, row: Any) -> list[tuple[str, Any]]:
        if hasattr(row, "primary_key"):
            return cls._pairs(row.primary_key)
        if isinstance(row, tuple) and len(row) == 2:
            return cls._pairs(row[0])
        raise AssertionError(f"Unsupported Row value: {row!r}")

    @classmethod
    def _attribute_columns(cls, row: Any) -> list[tuple[Any, ...]]:
        if hasattr(row, "attribute_columns"):
            return list(row.attribute_columns)
        if isinstance(row, tuple) and len(row) == 2:
            return list(row[1])
        raise AssertionError(f"Unsupported Row value: {row!r}")

    @classmethod
    def _payload(cls, row: Any) -> str:
        columns = cls._attribute_columns(row)
        payload_columns = [column for column in columns if column[0] == "payload"]
        assert len(payload_columns) == 1
        payload = payload_columns[0][1]
        assert isinstance(payload, str)
        json.loads(payload)
        return payload

    @staticmethod
    def _pairs(value: Any) -> list[tuple[str, Any]]:
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
            value = [value]
        return [(str(item[0]), item[1]) for item in value]

    @classmethod
    def _rank_primary_key(cls, primary_key: list[tuple[str, Any]]) -> tuple[Any, ...]:
        return tuple(cls._rank_value(value) for _, value in primary_key)

    @staticmethod
    def _rank_value(value: Any) -> tuple[int, str]:
        rendered = f"{type(value).__name__}:{value!r}".upper().replace("_", "")
        if "INFMIN" in rendered:
            return 0, ""
        if "INFMAX" in rendered:
            return 2, ""
        return 1, str(value)


def _memory(
    memory_id: str,
    *,
    team_id: str = "team-a",
    user_id: str = "user-a",
    updated_at: str = "2026-07-12T10:00:00+00:00",
    status: str = "active",
    value: str | None = None,
) -> ExperienceMemory:
    return ExperienceMemory(
        memory_id=memory_id,
        team_id=team_id,
        user_id=user_id,
        kind="preference",
        key=f"key-{memory_id}",
        value=value or f"value-{memory_id}",
        status=status,
        confidence=0.9,
        importance=4,
        source_session_id="session-source",
        source_reference="session:session-source",
        created_at="2026-07-12T09:00:00+00:00",
        updated_at=updated_at,
        valid_from="2026-07-12T09:00:00+00:00",
    )


def _decision(
    decision_id: str,
    *,
    team_id: str = "team-a",
    user_id: str = "user-a",
    created_at: str = "2026-07-12T10:00:00+00:00",
) -> ExperienceDecisionRecord:
    return ExperienceDecisionRecord(
        decision_id=decision_id,
        team_id=team_id,
        user_id=user_id,
        session_id=f"session-{decision_id}",
        requested_action="remember",
        action="remember",
        created_memory_id=f"memory-{decision_id}",
        rationale="Offline Tablestore repository test.",
        provider_name="test-policy",
        model_name="test-model",
        created_at=created_at,
    )


def _repository(
    client: _InMemoryTablestoreClient,
) -> TablestoreExperienceMemoryRepository:
    return TablestoreExperienceMemoryRepository(
        client=client,
        table_name="experience-memory-test",
    )


def test_round_trip_sorting_filtering_schema_and_pagination() -> None:
    client = _InMemoryTablestoreClient(page_size=1)
    repository = _repository(client)
    memories = [
        _memory(
            "memory-zulu",
            updated_at="2026-07-12T12:00:00+00:00",
            status="superseded",
        ),
        _memory("memory-old", updated_at="2026-07-12T10:00:00+00:00"),
        _memory("memory-alpha", updated_at="2026-07-12T12:00:00+00:00"),
    ]
    decisions = [
        _decision("decision-late-b", created_at="2026-07-12T12:00:00+00:00"),
        _decision("decision-early", created_at="2026-07-12T10:00:00+00:00"),
        _decision("decision-late-a", created_at="2026-07-12T12:00:00+00:00"),
    ]

    for memory in memories:
        assert repository.save_memory(memory) == memory
    for decision in decisions:
        assert repository.append_decision(decision) == decision

    assert repository.get_memory(
        "memory-old", team_id="team-a", user_id="user-a"
    ) == memories[1]
    assert [
        memory.memory_id
        for memory in repository.list_memories(team_id="team-a", user_id="user-a")
    ] == ["memory-alpha", "memory-zulu", "memory-old"]
    assert [
        memory.memory_id
        for memory in repository.list_memories(
            team_id="team-a",
            user_id="user-a",
            include_inactive=False,
        )
    ] == ["memory-alpha", "memory-old"]
    assert [
        decision.decision_id
        for decision in repository.list_decisions(team_id="team-a", user_id="user-a")
    ] == ["decision-early", "decision-late-a", "decision-late-b"]

    primary_keys = client.stored_primary_keys()
    assert all(
        [name for name, _ in primary_key] == ["scope_id", "record_id"]
        for primary_key in primary_keys
    )
    record_ids = {str(dict(primary_key)["record_id"]) for primary_key in primary_keys}
    assert record_ids == {
        *(f"m#{memory.memory_id}" for memory in memories),
        *(f"d#{decision.decision_id}" for decision in decisions),
    }
    assert {payload["schema_version"] for payload in client.stored_payloads()} == {
        "experience-memory-v1",
        "experience-decision-v1",
    }
    assert client.paginated_responses > 0


def test_transaction_commits_and_passes_transaction_id_to_all_sdk_calls() -> None:
    client = _InMemoryTablestoreClient(page_size=1)
    repository = _repository(client)
    memory = _memory("memory-committed")
    decision = _decision("decision-committed")

    with repository.transaction(team_id="team-a", user_id="user-a") as transaction:
        assert transaction.save_memory(memory) == memory
        assert transaction.append_decision(decision) == decision
        assert transaction.get_memory(memory.memory_id) == memory
        assert transaction.list_memories(team_id="team-a", user_id="user-a") == [
            memory
        ]
        assert transaction.list_decisions(team_id="team-a", user_id="user-a") == [
            decision
        ]
        transaction_calls = list(client.data_calls)

    transaction_id = client.started[0][2]
    assert transaction_calls
    assert {call.transaction_id for call in transaction_calls} == {transaction_id}
    assert client.committed == [transaction_id]
    assert client.aborted == []
    assert repository.get_memory(
        memory.memory_id,
        team_id=memory.team_id,
        user_id=memory.user_id,
    ) == memory


def test_transaction_aborts_on_exception_without_publishing_writes() -> None:
    client = _InMemoryTablestoreClient()
    repository = _repository(client)
    memory = _memory("memory-aborted")

    with pytest.raises(RuntimeError, match="force abort"):
        with repository.transaction(team_id="team-a", user_id="user-a") as transaction:
            transaction.save_memory(memory)
            raise RuntimeError("force abort")

    transaction_id = client.started[0][2]
    assert client.committed == []
    assert client.aborted == [transaction_id]
    assert {call.transaction_id for call in client.data_calls} == {transaction_id}
    with pytest.raises(NotFoundError):
        repository.get_memory(
            memory.memory_id,
            team_id=memory.team_id,
            user_id=memory.user_id,
        )


@pytest.mark.parametrize("record_kind", ["memory", "decision"])
def test_transaction_rejects_cross_scope_writes(record_kind: str) -> None:
    client = _InMemoryTablestoreClient()
    repository = _repository(client)

    with pytest.raises(DreamError):
        with repository.transaction(team_id="team-a", user_id="user-a") as transaction:
            if record_kind == "memory":
                transaction.save_memory(
                    _memory("memory-other-scope", team_id="team-b", user_id="user-a")
                )
            else:
                transaction.append_decision(
                    _decision(
                        "decision-other-scope",
                        team_id="team-a",
                        user_id="user-b",
                    )
                )

    assert client.data_calls == []
    assert client.committed == []
    assert client.aborted == [client.started[0][2]]


def test_scopes_are_isolated_even_when_record_ids_match() -> None:
    client = _InMemoryTablestoreClient(page_size=1)
    repository = _repository(client)
    first = _memory(
        "shared-memory",
        team_id="team-a",
        user_id="user-a",
        value="first scope",
    )
    second = _memory(
        "shared-memory",
        team_id="team-b",
        user_id="user-b",
        value="second scope",
    )
    first_decision = _decision(
        "shared-decision",
        team_id="team-a",
        user_id="user-a",
    )
    second_decision = _decision(
        "shared-decision",
        team_id="team-b",
        user_id="user-b",
    )

    repository.save_memory(first)
    repository.save_memory(second)
    repository.append_decision(first_decision)
    repository.append_decision(second_decision)

    assert repository.get_memory(
        first.memory_id,
        team_id=first.team_id,
        user_id=first.user_id,
    ) == first
    assert repository.get_memory(
        second.memory_id,
        team_id=second.team_id,
        user_id=second.user_id,
    ) == second
    assert repository.list_memories(team_id="team-a", user_id="user-a") == [first]
    assert repository.list_memories(team_id="team-b", user_id="user-b") == [second]
    assert repository.list_decisions(team_id="team-a", user_id="user-a") == [
        first_decision
    ]
    assert repository.list_decisions(team_id="team-b", user_id="user-b") == [
        second_decision
    ]
    with pytest.raises(NotFoundError):
        repository.get_memory(
            first.memory_id,
            team_id="team-a",
            user_id="user-b",
        )

    memory_primary_keys = [
        primary_key
        for primary_key in client.stored_primary_keys()
        if str(dict(primary_key)["record_id"]).startswith("m#")
    ]
    assert len({dict(primary_key)["scope_id"] for primary_key in memory_primary_keys}) == 2


def test_empty_sdk_wide_row_token_does_not_trigger_continuation_error() -> None:
    client = _InMemoryTablestoreClient()
    client.empty_next_token = b""
    repository = _repository(client)
    memory = _memory("memory-empty-token")

    repository.save_memory(memory)

    assert repository.list_memories(team_id="team-a", user_id="user-a") == [memory]
