# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.evals.rating import HumanRatingService


def test_audit_record_creation(tmp_path) -> None:
    repository = AuditRepository(tmp_path / "audit.sqlite")
    logger = AuditLogger(repository=repository)

    record = logger.log_generation(
        run_id="run-1",
        use_case="unit_test",
        team_id="demo_team",
        input_payload={"request": "demo"},
        retrieved_source_paths=["knowledge_packs/demo_team/docs/domain/job-execution-workflow.md"],
        model_provider="mock",
        model_name="mock-deterministic-v1",
        output_path="artifacts/demo.md",
        status="success",
        warnings=[],
    )

    assert record.input_hash
    assert repository.get_audit_record("run-1") == record
    assert repository.list_audit_records()[0].run_id == "run-1"


def test_human_rating_storage(tmp_path) -> None:
    repository = AuditRepository(tmp_path / "audit.sqlite")
    service = HumanRatingService(repository=repository)

    rating = service.rate(
        run_id="run-1",
        usefulness_score=4,
        correctness_score=3,
        comments="Useful draft but needs more specific test scenarios",
    )

    ratings = repository.list_ratings("run-1")
    assert ratings == [rating]
    assert ratings[0].usefulness_score == 4

