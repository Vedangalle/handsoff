"""Independent telemetry-based outcome verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.application.conditions import ConditionEvaluator
from handsoff.domain.execution import VerificationResult

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.application.world_model import WorldModel
    from handsoff.domain.goals import Goal


class OutcomeVerifier:
    """Evaluate goal acceptance conditions without planner judgment."""

    def __init__(self, world: WorldModel) -> None:
        """Bind the world state used as verification evidence."""
        self._world = world
        self._conditions = ConditionEvaluator()

    def verify(self, goal: Goal, now: datetime) -> tuple[VerificationResult, ...]:
        """Return one explicit result for every goal condition."""
        results: list[VerificationResult] = []
        for condition in goal.acceptance_conditions:
            check = self._conditions.evaluate(condition, self._world, now)
            results.append(
                VerificationResult(
                    condition_id=condition.condition_id,
                    satisfied=check.satisfied,
                    observation_ids=check.observation_ids,
                    evaluated_at=now,
                    reason=check.reason,
                )
            )
        return tuple(results)


__all__ = ["OutcomeVerifier"]
