"""Plan proposal graph and identity tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from tests.fixtures.contracts import NOW, make_action, make_condition, make_plan

TWO_ACTIONS = 2


def test_action_rejects_duplicate_dependencies() -> None:
    """One dependency cannot appear twice."""
    with pytest.raises(ValidationError, match="dependencies must be unique"):
        make_action(depends_on=("action.first", "action.first"))


def test_action_rejects_duplicate_acceptance_conditions() -> None:
    """Action acceptance-condition identifiers are unique."""
    condition = make_condition()
    with pytest.raises(ValidationError, match="condition identifiers must be unique"):
        make_action(acceptance_conditions=(condition, condition))


def test_plan_accepts_acyclic_dependency_graph() -> None:
    """Declared dependencies may form a deterministic directed acyclic graph."""
    first = make_action(action_id="action.first", idempotency_key="idempotency.first")
    second = make_action(
        action_id="action.second",
        idempotency_key="idempotency.second",
        depends_on=("action.first",),
    )
    assert len(make_plan(actions=(first, second)).actions) == TWO_ACTIONS


def test_plan_rejects_nonfuture_expiration() -> None:
    """Expired-at-creation proposals are invalid."""
    with pytest.raises(ValidationError, match="expiration must be later"):
        make_plan(expires_at=NOW)


def test_plan_rejects_duplicate_observation_ids() -> None:
    """The world-state snapshot identifies each observation once."""
    with pytest.raises(ValidationError, match="observation identifiers must be unique"):
        make_plan(world_state_observation_ids=("observation.initial", "observation.initial"))


def test_plan_rejects_duplicate_action_ids() -> None:
    """Action identifiers are unique within a plan."""
    with pytest.raises(ValidationError, match="action identifiers must be unique"):
        make_plan(actions=(make_action(), make_action(idempotency_key="idempotency.other")))


def test_plan_rejects_duplicate_idempotency_keys() -> None:
    """Two actions cannot share a dispatch identity."""
    with pytest.raises(ValidationError, match="idempotency keys must be unique"):
        make_plan(
            actions=(
                make_action(),
                make_action(action_id="action.other"),
            )
        )


def test_plan_rejects_self_dependency() -> None:
    """An action cannot wait on itself."""
    with pytest.raises(ValidationError, match="cannot depend on itself"):
        make_plan(actions=(make_action(depends_on=("action.prepare",)),))


def test_plan_rejects_undeclared_dependency() -> None:
    """Every dependency must name an action in the same plan."""
    with pytest.raises(ValidationError, match="undeclared action"):
        make_plan(actions=(make_action(depends_on=("action.missing",)),))


def test_plan_rejects_dependency_cycle() -> None:
    """Cyclic action graphs never become executable plans."""
    first = make_action(
        action_id="action.first",
        idempotency_key="idempotency.first",
        depends_on=("action.second",),
    )
    second = make_action(
        action_id="action.second",
        idempotency_key="idempotency.second",
        depends_on=("action.first",),
    )
    with pytest.raises(ValidationError, match="must be acyclic"):
        make_plan(actions=(first, second))


def test_plan_preserves_expiration_and_parameters() -> None:
    """Valid proposal data remains inspectable and immutable."""
    action = make_action(parameters={"target": 21.0})
    plan = make_plan(actions=(action,), expires_at=NOW + timedelta(minutes=2))
    assert plan.actions[0].parameters == {"target": 21.0}
