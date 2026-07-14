"""Scenario contract cross-reference and boundary tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from handsoff.domain.capabilities import (
    AuthorizationRequirement,
    AutonomyMode,
    RiskClass,
)
from handsoff.domain.execution import PlanState
from handsoff.domain.policies import PolicyDecision
from handsoff.domain.scenarios import (
    ScenarioExpectation,
    ScriptedCapabilityOutcome,
    ScriptedResult,
)
from tests.fixtures.contracts import (
    NOW,
    make_capability,
    make_condition,
    make_goal,
    make_observation,
    make_scenario,
)


def make_effect_outcome(**overrides: object) -> ScriptedCapabilityOutcome:
    """Build a valid observed-effect script entry."""
    values: dict[str, object] = {
        "capability_id": "device.prepare",
        "attempt": 1,
        "result": ScriptedResult.EFFECT_OBSERVED,
        "effect_observations": (
            make_observation(
                observation_id="observation.effect",
                observed_at=NOW + timedelta(seconds=1),
                value="ready",
            ),
        ),
    }
    values.update(overrides)
    return ScriptedCapabilityOutcome.model_validate(values)


def test_effect_observed_requires_evidence() -> None:
    """A scripted observed effect includes the observation it creates."""
    with pytest.raises(ValidationError, match="requires at least one"):
        make_effect_outcome(effect_observations=())


def test_non_effect_result_rejects_effect_observations() -> None:
    """Failure and timeout scripts cannot carry contradictory effect evidence."""
    with pytest.raises(ValidationError, match="only effect_observed"):
        make_effect_outcome(result=ScriptedResult.FAILED)


def test_failure_result_without_effect_is_valid() -> None:
    """A deterministic failure script has no effect observations."""
    outcome = make_effect_outcome(
        result=ScriptedResult.FAILED,
        effect_observations=(),
    )
    assert outcome.result is ScriptedResult.FAILED


@pytest.mark.parametrize(
    ("left", "right", "message"),
    [
        (
            {"dispatched_capability_ids": ("device.prepare",)},
            {"withheld_capability_ids": ("device.prepare",)},
            "both dispatched and withheld",
        ),
        (
            {"verified_condition_ids": ("condition.ready",)},
            {"unsatisfied_condition_ids": ("condition.ready",)},
            "both verified and unsatisfied",
        ),
    ],
)
def test_expectation_rejects_contradictory_sets(
    left: dict[str, object],
    right: dict[str, object],
    message: str,
) -> None:
    """Expected outcomes cannot classify one identifier two ways."""
    values: dict[str, object] = {
        "policy_decision": PolicyDecision.ALLOW,
        "terminal_plan_state": PlanState.SUCCEEDED,
    }
    values.update(left)
    values.update(right)
    with pytest.raises(ValidationError, match=message):
        ScenarioExpectation.model_validate(values)


@pytest.mark.parametrize(
    "field",
    [
        "dispatched_capability_ids",
        "withheld_capability_ids",
        "verified_condition_ids",
        "unsatisfied_condition_ids",
    ],
)
def test_expectation_rejects_duplicate_identifiers(field: str) -> None:
    """Each expectation set contains unique identifiers."""
    values: dict[str, object] = {
        "policy_decision": PolicyDecision.ALLOW,
        "terminal_plan_state": PlanState.SUCCEEDED,
        field: ("item.duplicate", "item.duplicate"),
    }
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        ScenarioExpectation.model_validate(values)


def test_minimal_scenario_is_valid() -> None:
    """The reference factory satisfies every cross-boundary invariant."""
    assert make_scenario().simulation_only


def test_scenario_rejects_duplicate_capabilities() -> None:
    """A scenario declares each capability once."""
    capability = make_capability()
    with pytest.raises(ValidationError, match="capability identifiers must be unique"):
        make_scenario(capabilities=(capability, capability))


def test_scenario_rejects_duplicate_initial_observations() -> None:
    """Initial world state contains unique observation evidence."""
    observation = make_observation()
    with pytest.raises(ValidationError, match="observation identifiers must be unique"):
        make_scenario(initial_observations=(observation, observation))


def test_scenario_rejects_duplicate_scripted_attempts() -> None:
    """One capability attempt has one deterministic scripted result."""
    outcome = make_effect_outcome()
    with pytest.raises(ValidationError, match="attempts must be unique"):
        make_scenario(scripted_outcomes=(outcome, outcome))


def test_scenario_rejects_undeclared_capability_reference() -> None:
    """Scripts and expectations cannot introduce undeclared authority."""
    outcome = make_effect_outcome(capability_id="device.undeclared")
    with pytest.raises(ValidationError, match="undeclared capability"):
        make_scenario(scripted_outcomes=(outcome,))


def test_scenario_rejects_undeclared_condition_reference() -> None:
    """Expected verification results name declared goal conditions."""
    expectation = ScenarioExpectation(
        policy_decision=PolicyDecision.ALLOW,
        terminal_plan_state=PlanState.SUCCEEDED,
        unsatisfied_condition_ids=("condition.undeclared",),
    )
    with pytest.raises(ValidationError, match="undeclared goal condition"):
        make_scenario(expected=expectation)


def test_scenario_requires_goal_at_clock_start() -> None:
    """A reference goal begins at the deterministic scenario epoch."""
    goal = make_goal(requested_at=NOW + timedelta(seconds=1))
    with pytest.raises(ValidationError, match="request time"):
        make_scenario(goal=goal)


def test_scenario_rejects_future_initial_observation() -> None:
    """Initial state cannot contain evidence from the future."""
    observation = make_observation(observed_at=NOW + timedelta(seconds=1))
    with pytest.raises(ValidationError, match="cannot occur after"):
        make_scenario(initial_observations=(observation,))


def test_scenario_rejects_effect_before_clock_start() -> None:
    """Scripted effects cannot predate the scenario."""
    outcome = make_effect_outcome(
        effect_observations=(
            make_observation(
                observation_id="observation.effect",
                observed_at=NOW - timedelta(seconds=1),
            ),
        )
    )
    with pytest.raises(ValidationError, match="cannot occur before"):
        make_scenario(scripted_outcomes=(outcome,))


def test_scenario_rejects_r3_capability() -> None:
    """Reference scenarios cannot simulate prohibited R3 behavior."""
    capability = make_capability(
        risk_class=RiskClass.R3,
        authorization=AuthorizationRequirement.PROHIBITED,
        supported_modes=frozenset(),
    )
    with pytest.raises(ValidationError, match="cannot declare R3"):
        make_scenario(capabilities=(capability,))


def test_scenario_rejects_non_simulation_capability_mode() -> None:
    """Reference fixtures cannot silently gain live or shadow authority."""
    capability = make_capability(supported_modes=frozenset({AutonomyMode.SHADOW}))
    with pytest.raises(ValidationError, match="simulation-only"):
        make_scenario(capabilities=(capability,))


@pytest.mark.parametrize(
    ("decision", "terminal"),
    [
        (PolicyDecision.DENY, PlanState.REJECTED),
        (PolicyDecision.REQUIRE_APPROVAL, PlanState.AWAITING_APPROVAL),
        (PolicyDecision.ALLOW, PlanState.SUCCEEDED),
        (PolicyDecision.ALLOW, PlanState.PARTIALLY_SUCCEEDED),
        (PolicyDecision.ALLOW, PlanState.FAILED),
        (PolicyDecision.ALLOW, PlanState.COMPENSATED),
    ],
)
def test_scenario_accepts_policy_consistent_terminal_state(
    decision: PolicyDecision,
    terminal: PlanState,
) -> None:
    """Every permitted policy-to-terminal mapping is representable."""
    expected = ScenarioExpectation(
        policy_decision=decision,
        terminal_plan_state=terminal,
    )
    assert make_scenario(expected=expected).expected.terminal_plan_state is terminal


def test_scenario_rejects_policy_inconsistent_terminal_state() -> None:
    """A denied scenario cannot claim successful completion."""
    expected = ScenarioExpectation(
        policy_decision=PolicyDecision.DENY,
        terminal_plan_state=PlanState.SUCCEEDED,
    )
    with pytest.raises(ValidationError, match="inconsistent"):
        make_scenario(expected=expected)


def test_scenario_accepts_scripted_effect_and_declared_references() -> None:
    """A complete script entry connects declared capability to future evidence."""
    scenario = make_scenario(scripted_outcomes=(make_effect_outcome(),))
    assert scenario.scripted_outcomes[0].effect_observations


def test_scenario_goal_conditions_can_be_replaced_consistently() -> None:
    """Cross-reference validation follows the goal contract rather than fixed names."""
    condition = make_condition(condition_id="condition.custom")
    goal = make_goal(acceptance_conditions=(condition,))
    expected = ScenarioExpectation(
        policy_decision=PolicyDecision.ALLOW,
        terminal_plan_state=PlanState.SUCCEEDED,
        verified_condition_ids=("condition.custom",),
    )
    assert make_scenario(goal=goal, expected=expected).goal == goal
