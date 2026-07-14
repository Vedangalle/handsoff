"""Capability registry and deterministic policy-kernel tests."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from handsoff.application.capability_registry import CapabilityRegistry
from handsoff.application.evaluate_plan import PolicyKernel
from handsoff.application.world_model import WorldModel
from handsoff.domain.capabilities import (
    AuthorizationRequirement,
    AutonomyMode,
    CapabilityParameter,
    ParameterType,
    RiskClass,
)
from handsoff.domain.policies import PolicyDecision
from tests.fixtures.contracts import (
    NOW,
    make_action,
    make_capability,
    make_condition,
    make_observation,
    make_plan,
)

if TYPE_CHECKING:
    from pydantic import JsonValue

EXPECTED_ACTION_ERROR_COUNT = 4


def make_parameter(**overrides: object) -> CapabilityParameter:
    """Build a required numeric parameter."""
    values: dict[str, object] = {
        "name": "target",
        "value_type": ParameterType.NUMBER,
        "description": "Requested target",
        "required": True,
        "minimum": 1.0,
        "maximum": 10.0,
    }
    values.update(overrides)
    return CapabilityParameter.model_validate(values)


def test_registry_rejects_duplicate_capability_version() -> None:
    """Exact declarations are unique."""
    capability = make_capability()
    with pytest.raises(ValueError, match="more than once"):
        CapabilityRegistry((capability, capability))


def test_registry_resolves_in_stable_order() -> None:
    """Lookup is exact and enumeration is deterministic."""
    first = make_capability(capability_id="alpha.prepare")
    second = make_capability(capability_id="zeta.prepare")
    registry = CapabilityRegistry((second, first))
    assert registry.resolve("alpha.prepare", "1.0.0") == first
    assert registry.resolve("alpha.prepare", "2.0.0") is None
    assert registry.contracts() == (first, second)


def test_registry_reports_unknown_capability() -> None:
    """Undeclared action references fail closed."""
    errors = CapabilityRegistry((make_capability(),)).validate_action(
        make_action(capability_id="unknown.prepare"),
        AutonomyMode.SIMULATION,
    )
    assert errors == ("capability identifier or version is not declared",)


def test_registry_reports_target_mode_and_parameter_shape_errors() -> None:
    """Target, mode, required, and undeclared parameter violations accumulate."""
    capability = make_capability(parameters=(make_parameter(),))
    action = make_action(target_entity_id="device.other", parameters={"extra": 1})
    errors = CapabilityRegistry((capability,)).validate_action(action, AutonomyMode.SHADOW)
    assert len(errors) == EXPECTED_ACTION_ERROR_COUNT
    assert any("target" in error for error in errors)
    assert any("mode" in error for error in errors)
    assert any("missing" in error for error in errors)
    assert any("undeclared" in error for error in errors)


@pytest.mark.parametrize(
    ("parameter", "value", "fragment"),
    [
        (make_parameter(), True, "type"),
        (make_parameter(allowed_values=(2.0, 3.0)), 4.0, "allowlist"),
        (make_parameter(), 0.5, "minimum"),
        (make_parameter(), 11.0, "maximum"),
        (make_parameter(value_type=ParameterType.BOOLEAN, minimum=None, maximum=None), 1, "type"),
        (make_parameter(value_type=ParameterType.INTEGER, minimum=None, maximum=None), 1.5, "type"),
        (make_parameter(value_type=ParameterType.STRING, minimum=None, maximum=None), 1, "type"),
    ],
)
def test_registry_rejects_invalid_parameter_values(
    parameter: CapabilityParameter,
    value: JsonValue,
    fragment: str,
) -> None:
    """Runtime parameter checks mirror declared scalar constraints."""
    capability = make_capability(parameters=(parameter,))
    errors = CapabilityRegistry((capability,)).validate_action(
        make_action(parameters={"target": value}),
        AutonomyMode.SIMULATION,
    )
    assert fragment in errors[0]


def test_registry_accepts_valid_optional_and_required_parameters() -> None:
    """A contract-valid scalar request has no violations."""
    required = make_parameter(allowed_values=(2.0, 3.0))
    optional = make_parameter(
        name="label", value_type=ParameterType.STRING, required=False, minimum=None, maximum=None
    )
    capability = make_capability(parameters=(required, optional))
    action = make_action(parameters={"target": 2.0, "label": "arrival"})
    assert CapabilityRegistry((capability,)).validate_action(action, AutonomyMode.SIMULATION) == ()


def test_policy_allows_valid_simulation_action() -> None:
    """Declared R1 simulation actions are deterministically allowed."""
    registry = CapabilityRegistry((make_capability(),))
    policy = PolicyKernel(registry, WorldModel((make_observation(),))).evaluate(make_plan(), NOW)
    assert policy.decision is PolicyDecision.ALLOW
    assert policy.inputs_considered == (
        "device.prepare",
        "plan.arrival",
    )


def test_policy_requires_explicit_approval_when_declared() -> None:
    """Approval requirements propagate to the aggregate decision."""
    capability = make_capability(authorization=AuthorizationRequirement.APPROVAL)
    policy = PolicyKernel(
        CapabilityRegistry((capability,)),
        WorldModel((make_observation(),)),
    ).evaluate(make_plan(), NOW)
    assert policy.decision is PolicyDecision.REQUIRE_APPROVAL


def test_policy_denies_unknown_capability_as_prohibited_risk() -> None:
    """Hallucinated capability references are denied before dispatch."""
    plan = make_plan(actions=(make_action(capability_id="unknown.prepare"),))
    policy = PolicyKernel(
        CapabilityRegistry((make_capability(),)),
        WorldModel((make_observation(),)),
    ).evaluate(plan, NOW)
    assert policy.decision is PolicyDecision.DENY
    assert policy.action_decisions[0].risk_class is RiskClass.R3


def test_policy_denies_expired_plan() -> None:
    """Expiration at the evaluation instant fails closed."""
    plan = make_plan(
        created_at=NOW - timedelta(minutes=2),
        expires_at=NOW,
    )
    policy = PolicyKernel(
        CapabilityRegistry((make_capability(),)),
        WorldModel((make_observation(),)),
    ).evaluate(plan, NOW)
    assert policy.decision is PolicyDecision.DENY
    assert "expired" in policy.action_decisions[0].reasons[0]


def test_policy_denies_prohibited_r3_capability() -> None:
    """R3 and prohibited declarations produce explicit denial reasons."""
    capability = make_capability(
        risk_class=RiskClass.R3,
        authorization=AuthorizationRequirement.PROHIBITED,
        supported_modes=frozenset(),
    )
    policy = PolicyKernel(
        CapabilityRegistry((capability,)),
        WorldModel((make_observation(),)),
    ).evaluate(make_plan(), NOW)
    reasons = policy.action_decisions[0].reasons
    assert any("R3" in reason for reason in reasons)
    assert any("prohibited" in reason for reason in reasons)


def test_policy_denies_unsatisfied_precondition_and_records_evidence() -> None:
    """Capability and action preconditions are deduplicated and evidence-linked."""
    condition = make_condition(target_value="ready")
    capability = make_capability(preconditions=(condition,))
    action = make_action(preconditions=(condition,))
    policy = PolicyKernel(
        CapabilityRegistry((capability,)),
        WorldModel((make_observation(value="idle"),)),
    ).evaluate(make_plan(actions=(action,)), NOW)
    assert policy.decision is PolicyDecision.DENY
    assert "observation.initial" in policy.inputs_considered
