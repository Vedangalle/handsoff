"""Policy-result and approval contract tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from handsoff.domain.capabilities import RiskClass
from handsoff.domain.policies import Approval, PolicyDecision
from tests.fixtures.contracts import (
    NOW,
    make_action_decision,
    make_policy_evaluation,
)


def test_r3_action_decision_must_deny() -> None:
    """R3 can never be allowed or approval-gated."""
    with pytest.raises(ValidationError, match="must be deny"):
        make_action_decision(risk_class=RiskClass.R3)


def test_r3_deny_decision_is_valid() -> None:
    """A denied R3 proposal remains representable as evidence."""
    result = make_action_decision(
        risk_class=RiskClass.R3,
        decision=PolicyDecision.DENY,
    )
    assert result.decision is PolicyDecision.DENY


def test_policy_rejects_duplicate_action_decisions() -> None:
    """One policy evaluation contains one result per action."""
    decision = make_action_decision()
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        make_policy_evaluation(action_decisions=(decision, decision))


def test_policy_rejects_duplicate_input_identifiers() -> None:
    """A policy trace identifies each considered input once."""
    with pytest.raises(ValidationError, match="input identifiers must be unique"):
        make_policy_evaluation(inputs_considered=("observation.initial", "observation.initial"))


@pytest.mark.parametrize(
    ("action_decision", "aggregate"),
    [
        (PolicyDecision.ALLOW, PolicyDecision.ALLOW),
        (PolicyDecision.REQUIRE_APPROVAL, PolicyDecision.REQUIRE_APPROVAL),
        (PolicyDecision.DENY, PolicyDecision.DENY),
    ],
)
def test_policy_accepts_consistent_aggregate(
    action_decision: PolicyDecision,
    aggregate: PolicyDecision,
) -> None:
    """The plan result deterministically aggregates its action results."""
    result = make_policy_evaluation(
        decision=aggregate,
        action_decisions=(make_action_decision(decision=action_decision),),
    )
    assert result.decision is aggregate


@pytest.mark.parametrize(
    ("action_decision", "incorrect_aggregate"),
    [
        (PolicyDecision.ALLOW, PolicyDecision.DENY),
        (PolicyDecision.REQUIRE_APPROVAL, PolicyDecision.ALLOW),
        (PolicyDecision.DENY, PolicyDecision.REQUIRE_APPROVAL),
    ],
)
def test_policy_rejects_inconsistent_aggregate(
    action_decision: PolicyDecision,
    incorrect_aggregate: PolicyDecision,
) -> None:
    """A contradictory plan-level policy result is schema-invalid."""
    with pytest.raises(ValidationError, match="must aggregate"):
        make_policy_evaluation(
            decision=incorrect_aggregate,
            action_decisions=(make_action_decision(decision=action_decision),),
        )


def test_deny_dominates_approval_and_allow() -> None:
    """Any denied action forces the aggregate plan result to deny."""
    decisions = (
        make_action_decision(action_id="action.allow"),
        make_action_decision(
            action_id="action.approval",
            decision=PolicyDecision.REQUIRE_APPROVAL,
        ),
        make_action_decision(action_id="action.deny", decision=PolicyDecision.DENY),
    )
    result = make_policy_evaluation(
        decision=PolicyDecision.DENY,
        action_decisions=decisions,
    )
    assert result.decision is PolicyDecision.DENY


def test_approval_dominates_allow_without_denial() -> None:
    """An approval-gated action makes the plan approval-gated."""
    decisions = (
        make_action_decision(action_id="action.allow"),
        make_action_decision(
            action_id="action.approval",
            decision=PolicyDecision.REQUIRE_APPROVAL,
        ),
    )
    result = make_policy_evaluation(
        decision=PolicyDecision.REQUIRE_APPROVAL,
        action_decisions=decisions,
    )
    assert result.decision is PolicyDecision.REQUIRE_APPROVAL


def make_approval(**overrides: object) -> Approval:
    """Build a valid bounded approval."""
    values: dict[str, object] = {
        "approval_id": "approval.arrival",
        "plan_id": "plan.arrival",
        "policy_evaluation_id": "policy-evaluation.arrival",
        "approver_id": "user.owner",
        "approved_action_ids": ("action.prepare",),
        "issued_at": NOW,
        "expires_at": NOW + timedelta(minutes=1),
    }
    values.update(overrides)
    return Approval.model_validate(values)


def test_approval_accepts_future_expiration_and_unique_actions() -> None:
    """A valid approval is time-bounded and scoped."""
    assert make_approval().approver_id == "user.owner"


def test_approval_rejects_nonfuture_expiration() -> None:
    """Expired authorization cannot be represented as valid approval."""
    with pytest.raises(ValidationError, match="later than issue"):
        make_approval(expires_at=NOW)


def test_approval_rejects_duplicate_actions() -> None:
    """An approval scope identifies each action once."""
    with pytest.raises(ValidationError, match="must be unique"):
        make_approval(approved_action_ids=("action.prepare", "action.prepare"))
