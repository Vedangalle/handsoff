"""Acceptance-condition and goal contract tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from handsoff.domain.goals import AcceptanceCondition, ConditionOperator
from tests.fixtures.contracts import NOW, make_condition, make_goal

TEMPERATURE_TOLERANCE = 0.5


@pytest.mark.parametrize("operator", [ConditionOperator.IS_TRUE, ConditionOperator.IS_FALSE])
def test_truth_conditions_need_no_arguments(operator: ConditionOperator) -> None:
    """Truth operators accept no target-specific arguments."""
    condition = make_condition(
        operator=operator,
        target_value=None,
        unit=None,
        tolerance=None,
    )
    assert condition.operator is operator


@pytest.mark.parametrize(
    ("field", "value"),
    [("target_value", True), ("unit", "state"), ("tolerance", 0.0)],
)
def test_truth_conditions_reject_arguments(field: str, value: object) -> None:
    """Truth operators reject target, unit, and tolerance fields."""
    overrides: dict[str, object] = {
        "operator": ConditionOperator.IS_TRUE,
        "target_value": None,
    }
    overrides[field] = value
    with pytest.raises(ValidationError, match="truth operators"):
        make_condition(**overrides)


def test_comparison_requires_target() -> None:
    """Non-truth comparisons require a target value."""
    with pytest.raises(ValidationError, match="require target_value"):
        make_condition(target_value=None)


@pytest.mark.parametrize("target", [True, "twenty"])
def test_within_requires_numeric_target(target: object) -> None:
    """The within operator rejects Boolean and string targets."""
    with pytest.raises(ValidationError, match="numeric target and tolerance"):
        make_condition(operator=ConditionOperator.WITHIN, target_value=target, tolerance=1.0)


def test_within_requires_tolerance() -> None:
    """The within operator requires an explicit tolerance."""
    with pytest.raises(ValidationError, match="numeric target and tolerance"):
        make_condition(operator=ConditionOperator.WITHIN, target_value=20.0)


def test_within_accepts_numeric_target_and_tolerance() -> None:
    """A numeric within condition is schema-valid."""
    condition = make_condition(
        operator=ConditionOperator.WITHIN,
        target_value=20.0,
        tolerance=TEMPERATURE_TOLERANCE,
        unit="degrees_celsius",
    )
    assert condition.tolerance == TEMPERATURE_TOLERANCE


def test_other_operators_reject_tolerance() -> None:
    """Tolerance cannot silently modify equality semantics."""
    with pytest.raises(ValidationError, match="valid only for the within"):
        make_condition(tolerance=0.5)


def test_condition_rejects_unknown_fields_and_mutation() -> None:
    """Trust-boundary contracts reject undeclared data and remain immutable."""
    data = make_condition().model_dump()
    data["unexpected"] = "value"
    with pytest.raises(ValidationError, match="Extra inputs"):
        AcceptanceCondition.model_validate(data)
    with pytest.raises(ValidationError, match="frozen"):
        make_condition().description = "changed"


def test_goal_accepts_unique_conditions_and_future_deadline() -> None:
    """A well-ordered goal contract is valid."""
    goal = make_goal()
    assert goal.deadline == NOW + timedelta(minutes=5)


def test_goal_rejects_duplicate_condition_ids() -> None:
    """Acceptance-condition identifiers are unique within a goal."""
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        make_goal(acceptance_conditions=(make_condition(), make_condition()))


@pytest.mark.parametrize("deadline", [NOW, NOW - timedelta(seconds=1)])
def test_goal_rejects_nonfuture_deadline(deadline: object) -> None:
    """A goal deadline must be later than its request time."""
    with pytest.raises(ValidationError, match="deadline must be later"):
        make_goal(deadline=deadline)
