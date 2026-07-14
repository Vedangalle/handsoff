"""Pure evaluation of acceptance conditions against timestamped observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeGuard, cast

from handsoff.domain.goals import AcceptanceCondition, ConditionOperator
from handsoff.domain.observations import ObservationQuality

if TYPE_CHECKING:
    from datetime import datetime

    from pydantic import JsonValue

    from handsoff.application.world_model import WorldModel


@dataclass(frozen=True, slots=True)
class ConditionCheck:
    """Deterministic condition result and the evidence used to reach it."""

    satisfied: bool
    observation_ids: tuple[str, ...]
    reason: str


def _is_number(value: object) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float))


class ConditionEvaluator:
    """Evaluate one declared condition; missing or weak evidence fails closed."""

    def evaluate(  # noqa: PLR0911 - fail-closed evidence gates are intentionally explicit
        self,
        condition: AcceptanceCondition,
        world: WorldModel,
        now: datetime,
    ) -> ConditionCheck:
        """Evaluate using the newest matching observation."""
        observation = world.latest(condition.entity_id, condition.property_id)
        if observation is None:
            return ConditionCheck(
                satisfied=False,
                observation_ids=(),
                reason="required observation is missing",
            )
        evidence = (observation.observation_id,)
        age_seconds = (now - observation.observed_at).total_seconds()
        if age_seconds < 0:
            return ConditionCheck(
                satisfied=False,
                observation_ids=evidence,
                reason="observation timestamp is in the future",
            )
        if age_seconds > observation.freshness_limit_seconds:
            return ConditionCheck(
                satisfied=False,
                observation_ids=evidence,
                reason="observation is stale",
            )
        if observation.quality is ObservationQuality.UNKNOWN:
            return ConditionCheck(
                satisfied=False,
                observation_ids=evidence,
                reason="observation quality is unknown",
            )
        if observation.confidence <= 0:
            return ConditionCheck(
                satisfied=False,
                observation_ids=evidence,
                reason="observation confidence is zero",
            )
        if condition.unit is not None and observation.unit != condition.unit:
            return ConditionCheck(
                satisfied=False,
                observation_ids=evidence,
                reason="observation unit does not match condition",
            )

        satisfied = self._compare(condition, observation.value)
        reason = "condition satisfied" if satisfied else "observed value does not satisfy condition"
        return ConditionCheck(
            satisfied=satisfied,
            observation_ids=evidence,
            reason=reason,
        )

    @staticmethod
    def _compare(  # noqa: C901, PLR0911 - exhaustive operator dispatch is clearer inline
        condition: AcceptanceCondition,
        observed: JsonValue,
    ) -> bool:
        """Apply the operator without implicit Boolean-to-number coercion."""
        operator = condition.operator
        target = condition.target_value
        if operator is ConditionOperator.IS_TRUE:
            return observed is True
        if operator is ConditionOperator.IS_FALSE:
            return observed is False
        if operator is ConditionOperator.EQUALS:
            return observed == target and type(observed) is type(target)
        if operator is ConditionOperator.NOT_EQUALS:
            return observed != target or type(observed) is not type(target)
        if not _is_number(observed) or not _is_number(target):
            return False
        if operator is ConditionOperator.LESS_THAN:
            return observed < target
        if operator is ConditionOperator.LESS_THAN_OR_EQUAL:
            return observed <= target
        if operator is ConditionOperator.GREATER_THAN:
            return observed > target
        if operator is ConditionOperator.GREATER_THAN_OR_EQUAL:
            return observed >= target
        if operator is ConditionOperator.WITHIN:
            tolerance = cast("float", condition.tolerance)
            return abs(observed - target) <= tolerance
        return False  # type: ignore[unreachable]  # pragma: no cover


__all__ = ["ConditionCheck", "ConditionEvaluator"]
