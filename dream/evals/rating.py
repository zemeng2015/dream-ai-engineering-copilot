# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime

from dream.audit.repository import AuditRepository
from dream.evals.models import HumanRating


class HumanRatingService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self.repository = repository or AuditRepository()

    def rate(
        self,
        *,
        run_id: str,
        usefulness_score: int,
        correctness_score: int,
        comments: str,
    ) -> HumanRating:
        rating = HumanRating(
            run_id=run_id,
            usefulness_score=usefulness_score,
            correctness_score=correctness_score,
            comments=comments,
            created_at=datetime.now(UTC).isoformat(),
        )
        self.repository.add_rating(rating)
        return rating
