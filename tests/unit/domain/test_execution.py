"""Fail-first policy-adjacent state-transition contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from handsoff.domain.execution import (
    ActionState,
    ActionTransition,
    PlanState,
    PlanTransition,
    VerificationResult,
)
from tests.fixtures.contracts import NOW


def test_every_declared_plan_transition_is_schema_valid() -> None:
    """The complete approved plan graph is executable as contract data."""
    for from_state, destinations in PlanTransition.LEGAL_TRANSITIONS.items():
        for to_state in destinations:
            transition = PlanTransition(
                plan_id="plan.arrival",
                from_state=from_state,
                to_state=to_state,
                occurred_at=NOW,
                reason="Contract transition test",
            )
            assert transition.to_state is to_state


def test_every_undeclared_plan_transition_is_rejected() -> None:
    """Terminal, backward, and bypass plan transitions fail closed."""
    for from_state in PlanState:
        allowed = PlanTransition.LEGAL_TRANSITIONS.get(from_state, frozenset())
        for to_state in set(PlanState) - set(allowed):
            with pytest.raises(ValidationError, match="illegal plan"):
                PlanTransition(
                    plan_id="plan.arrival",
                    from_state=from_state,
                    to_state=to_state,
                    occurred_at=NOW,
                    reason="Contract rejection test",
                )


def test_every_declared_action_transition_is_schema_valid() -> None:
    """The complete approved action graph is executable as contract data."""
    for from_state, destinations in ActionTransition.LEGAL_TRANSITIONS.items():
        for to_state in destinations:
            transition = ActionTransition(
                action_id="action.prepare",
                from_state=from_state,
                to_state=to_state,
                occurred_at=NOW,
                reason="Contract transition test",
            )
            assert transition.to_state is to_state


def test_every_undeclared_action_transition_is_rejected() -> None:
    """Authorization and evidence states cannot be bypassed."""
    for from_state in ActionState:
        allowed = ActionTransition.LEGAL_TRANSITIONS.get(from_state, frozenset())
        for to_state in set(ActionState) - set(allowed):
            with pytest.raises(ValidationError, match="illegal action"):
                ActionTransition(
                    action_id="action.prepare",
                    from_state=from_state,
                    to_state=to_state,
                    occurred_at=NOW,
                    reason="Contract rejection test",
                )


def test_verification_result_accepts_unique_evidence() -> None:
    """Verification cites the observations used to reach its result."""
    result = VerificationResult(
        condition_id="condition.ready",
        satisfied=True,
        observation_ids=("observation.after",),
        evaluated_at=NOW,
        reason="Fresh simulated telemetry satisfies the condition",
    )
    assert result.satisfied


def test_verification_result_accepts_empty_evidence_for_missing_state() -> None:
    """A failed missing-observation check does not invent evidence."""
    result = VerificationResult(
        condition_id="condition.ready",
        satisfied=False,
        observation_ids=(),
        evaluated_at=NOW,
        reason="Required observation is missing",
    )
    assert result.observation_ids == ()


def test_verification_result_rejects_duplicate_evidence() -> None:
    """Evidence identifiers cannot be duplicated to inflate a trace."""
    with pytest.raises(ValidationError, match="must be unique"):
        VerificationResult(
            condition_id="condition.ready",
            satisfied=False,
            observation_ids=("observation.after", "observation.after"),
            evaluated_at=NOW,
            reason="Duplicate evidence is invalid",
        )
