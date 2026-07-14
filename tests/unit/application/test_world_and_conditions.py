"""World-model and pure condition-evaluation tests."""

from __future__ import annotations

from datetime import timedelta

import pytest

from handsoff.application.conditions import ConditionEvaluator
from handsoff.application.world_model import WorldModel
from handsoff.domain.goals import ConditionOperator
from handsoff.domain.observations import ObservationQuality
from tests.fixtures.contracts import NOW, make_condition, make_observation


def test_world_model_orders_evidence_and_handles_idempotent_duplicates() -> None:
    """Latest state is deterministic and identical replay is harmless."""
    older = make_observation(observation_id="observation.older")
    newer = make_observation(
        observation_id="observation.newer",
        observed_at=NOW + timedelta(seconds=1),
        value="ready",
    )
    world = WorldModel((older, newer))

    assert world.latest("device.primary", "state") == newer
    assert world.get(older.observation_id) == older
    assert world.get("observation.missing") is None
    assert world.record(newer) is False
    assert [item.observation_id for item in world.observations()] == [
        "observation.newer",
        "observation.older",
    ]


def test_world_model_rejects_identifier_reuse_with_different_evidence() -> None:
    """One observation identifier cannot be rewritten."""
    world = WorldModel((make_observation(),))
    with pytest.raises(ValueError, match="different evidence"):
        world.record(make_observation(value="changed"))


def test_world_model_returns_none_for_unknown_property() -> None:
    """An undeclared property has no implicit state."""
    assert WorldModel().latest("device.primary", "state") is None


@pytest.mark.parametrize(
    ("operator", "observed", "target", "expected"),
    [
        (ConditionOperator.EQUALS, "ready", "ready", True),
        (ConditionOperator.EQUALS, 1, 1.0, False),
        (ConditionOperator.NOT_EQUALS, "idle", "ready", True),
        (ConditionOperator.NOT_EQUALS, 1, 1.0, True),
        (ConditionOperator.LESS_THAN, 1.0, 2.0, True),
        (ConditionOperator.LESS_THAN_OR_EQUAL, 2.0, 2.0, True),
        (ConditionOperator.GREATER_THAN, 3.0, 2.0, True),
        (ConditionOperator.GREATER_THAN_OR_EQUAL, 2.0, 2.0, True),
        (ConditionOperator.LESS_THAN, "one", 2.0, False),
    ],
)
def test_condition_evaluator_comparison_operators(
    operator: ConditionOperator,
    observed: object,
    target: object,
    expected: object,
) -> None:
    """Comparisons are deterministic and never coerce Boolean/numeric types."""
    condition = make_condition(operator=operator, target_value=target)
    world = WorldModel((make_observation(value=observed),))
    result = ConditionEvaluator().evaluate(condition, world, NOW)
    assert result.satisfied is expected
    assert result.observation_ids == ("observation.initial",)


@pytest.mark.parametrize(
    ("operator", "value", "expected"),
    [
        (ConditionOperator.IS_TRUE, True, True),
        (ConditionOperator.IS_TRUE, False, False),
        (ConditionOperator.IS_FALSE, False, True),
        (ConditionOperator.IS_FALSE, True, False),
    ],
)
def test_condition_evaluator_truth_operators(
    operator: ConditionOperator,
    value: object,
    expected: object,
) -> None:
    """Truth checks require exact Boolean observations."""
    condition = make_condition(operator=operator, target_value=None)
    result = ConditionEvaluator().evaluate(
        condition,
        WorldModel((make_observation(value=value),)),
        NOW,
    )
    assert result.satisfied is expected


def test_condition_evaluator_within_is_inclusive() -> None:
    """A value exactly at tolerance is satisfied."""
    condition = make_condition(
        operator=ConditionOperator.WITHIN,
        target_value=10.0,
        tolerance=0.5,
    )
    result = ConditionEvaluator().evaluate(
        condition,
        WorldModel((make_observation(value=10.5),)),
        NOW,
    )
    assert result.satisfied


@pytest.mark.parametrize(
    ("observation_overrides", "now", "reason"),
    [
        ({"observed_at": NOW + timedelta(seconds=1)}, NOW, "future"),
        ({"observed_at": NOW - timedelta(seconds=31)}, NOW, "stale"),
        ({"quality": ObservationQuality.UNKNOWN}, NOW, "quality"),
        ({"confidence": 0.0}, NOW, "confidence"),
        ({"unit": "kelvin"}, NOW, "unit"),
    ],
)
def test_condition_evaluator_fails_closed_on_weak_evidence(
    observation_overrides: dict[str, object],
    now: object,
    reason: str,
) -> None:
    """Future, stale, unknown, zero-confidence, and wrong-unit evidence fails."""
    condition = make_condition(unit="degrees_celsius")
    values: dict[str, object] = {"unit": "degrees_celsius", **observation_overrides}
    observation = make_observation(**values)
    result = ConditionEvaluator().evaluate(condition, WorldModel((observation,)), now)  # type: ignore[arg-type]
    assert not result.satisfied
    assert reason in result.reason


def test_condition_evaluator_reports_missing_observation_without_evidence() -> None:
    """Missing state is explicit and carries no fabricated observation ID."""
    result = ConditionEvaluator().evaluate(make_condition(), WorldModel(), NOW)
    assert result.observation_ids == ()
    assert result.reason == "required observation is missing"
