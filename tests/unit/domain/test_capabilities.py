"""Capability contract invariant tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from handsoff.domain.capabilities import (
    AuthorizationRequirement,
    AutonomyMode,
    CapabilityParameter,
    IdempotencyBehavior,
    OperationClass,
    ParameterType,
    RiskClass,
)
from tests.fixtures.contracts import make_capability, make_condition

MAXIMUM_TARGET = 100.0


def make_parameter(**overrides: object) -> CapabilityParameter:
    """Build a valid numeric parameter."""
    values: dict[str, object] = {
        "name": "target",
        "value_type": ParameterType.NUMBER,
        "description": "Simulated target value",
        "required": True,
        "minimum": 0.0,
        "maximum": MAXIMUM_TARGET,
    }
    values.update(overrides)
    return CapabilityParameter.model_validate(values)


def test_parameter_accepts_ordered_numeric_bounds() -> None:
    """Numeric parameter bounds are preserved."""
    assert make_parameter().maximum == MAXIMUM_TARGET


def test_parameter_rejects_bounds_for_nonnumeric_type() -> None:
    """String and Boolean parameters cannot declare numeric bounds."""
    with pytest.raises(ValidationError, match="only for numeric"):
        make_parameter(value_type=ParameterType.STRING)


def test_parameter_rejects_reversed_bounds() -> None:
    """Minimum cannot exceed maximum."""
    with pytest.raises(ValidationError, match="cannot exceed"):
        make_parameter(minimum=2.0, maximum=1.0)


@pytest.mark.parametrize(
    ("value_type", "allowed_value"),
    [
        (ParameterType.BOOLEAN, True),
        (ParameterType.INTEGER, 1),
        (ParameterType.NUMBER, 1.5),
        (ParameterType.STRING, "ready"),
    ],
)
def test_parameter_accepts_allowed_value_matching_declared_type(
    value_type: ParameterType,
    allowed_value: object,
) -> None:
    """Allowed scalar values preserve the declared parameter type."""
    parameter = make_parameter(
        value_type=value_type,
        minimum=None,
        maximum=None,
        allowed_values=(allowed_value,),
    )
    assert parameter.allowed_values == (allowed_value,)


@pytest.mark.parametrize(
    ("value_type", "invalid_value"),
    [
        (ParameterType.BOOLEAN, 1),
        (ParameterType.INTEGER, True),
        (ParameterType.NUMBER, True),
        (ParameterType.STRING, 1.0),
    ],
)
def test_parameter_rejects_allowed_value_with_wrong_type(
    value_type: ParameterType,
    invalid_value: object,
) -> None:
    """Allowed-value declarations cannot contradict value_type."""
    with pytest.raises(ValidationError, match="does not match value_type"):
        make_parameter(
            value_type=value_type,
            minimum=None,
            maximum=None,
            allowed_values=(invalid_value,),
        )


def test_parameter_rejects_duplicate_allowed_values() -> None:
    """Allowed values are a deterministic set rather than a weighted list."""
    with pytest.raises(ValidationError, match="must be unique"):
        make_parameter(allowed_values=(1.0, 1.0))


def test_parameter_rejects_nonfinite_allowed_number() -> None:
    """Allowed numeric values cannot contain infinity or NaN."""
    with pytest.raises(ValidationError, match="must be finite"):
        make_parameter(allowed_values=(float("inf"),))


@pytest.mark.parametrize(
    ("allowed_value", "message"),
    [(-1.0, "below minimum"), (101.0, "above maximum")],
)
def test_parameter_rejects_allowed_value_outside_bounds(
    allowed_value: float,
    message: str,
) -> None:
    """Allowed numeric values remain inside declared bounds."""
    with pytest.raises(ValidationError, match=message):
        make_parameter(allowed_values=(allowed_value,))


def test_capability_rejects_duplicate_parameter_names() -> None:
    """Capability parameter names are unambiguous."""
    parameter = make_parameter()
    with pytest.raises(ValidationError, match="parameter names must be unique"):
        make_capability(parameters=(parameter, parameter))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("preconditions", "precondition identifiers"),
        ("expected_effects", "expected effect identifiers"),
        ("completion_evidence", "completion evidence identifiers"),
    ],
)
def test_capability_rejects_duplicate_condition_ids(field: str, message: str) -> None:
    """Every capability condition collection uses unique identifiers."""
    condition = make_condition()
    with pytest.raises(ValidationError, match=message):
        make_capability(**{field: (condition, condition)})


def test_r0_capability_is_read_only_and_needs_no_authorization() -> None:
    """A valid R0 contract is a read operation with no action authority."""
    capability = make_capability(
        operation=OperationClass.READ,
        risk_class=RiskClass.R0,
        authorization=AuthorizationRequirement.NONE,
        expected_effects=(),
        completion_evidence=(),
        idempotency=IdempotencyBehavior.NOT_APPLICABLE,
    )
    assert capability.risk_class is RiskClass.R0


def test_r0_rejects_write_operation() -> None:
    """R0 cannot be used to misclassify a state-changing capability."""
    with pytest.raises(ValidationError, match="must be read-only"):
        make_capability(risk_class=RiskClass.R0)


def test_r0_rejects_action_authorization() -> None:
    """Read-only observation does not use action approval semantics."""
    with pytest.raises(ValidationError, match="cannot require action authorization"):
        make_capability(
            operation=OperationClass.READ,
            risk_class=RiskClass.R0,
            authorization=AuthorizationRequirement.APPROVAL,
            expected_effects=(),
            completion_evidence=(),
            idempotency=IdempotencyBehavior.NOT_APPLICABLE,
        )


def test_r2_requires_approval_or_prohibition_outside_simulation() -> None:
    """Consequential non-simulated actions cannot be silently authorized."""
    with pytest.raises(ValidationError, match="outside simulation"):
        make_capability(
            risk_class=RiskClass.R2,
            supported_modes=frozenset({AutonomyMode.SUPERVISED}),
        )


def test_r2_can_run_without_approval_only_in_simulation() -> None:
    """Simulation can exercise R2 logic without granting physical authority."""
    capability = make_capability(risk_class=RiskClass.R2)
    assert capability.supported_modes == frozenset({AutonomyMode.SIMULATION})


def test_r2_approval_contract_is_valid_in_simulation() -> None:
    """R2 may be represented as approval-gated simulated behavior."""
    capability = make_capability(
        risk_class=RiskClass.R2,
        authorization=AuthorizationRequirement.APPROVAL,
    )
    assert capability.authorization is AuthorizationRequirement.APPROVAL


def test_r3_requires_prohibition() -> None:
    """No R3 capability can be represented as executable."""
    with pytest.raises(ValidationError, match="must be prohibited"):
        make_capability(risk_class=RiskClass.R3)


def test_r3_rejects_supported_modes() -> None:
    """A prohibited R3 declaration supports no autonomy mode."""
    with pytest.raises(ValidationError, match="cannot support"):
        make_capability(
            risk_class=RiskClass.R3,
            authorization=AuthorizationRequirement.PROHIBITED,
        )


def test_prohibited_r3_contract_with_no_modes_is_valid() -> None:
    """R3 vocabulary may exist only as an explicitly prohibited contract."""
    capability = make_capability(
        risk_class=RiskClass.R3,
        authorization=AuthorizationRequirement.PROHIBITED,
        supported_modes=frozenset(),
    )
    assert not capability.supported_modes


def test_write_requires_idempotency_behavior() -> None:
    """Write contracts cannot omit duplicate-effect protection."""
    with pytest.raises(ValidationError, match="explicit idempotency"):
        make_capability(idempotency=IdempotencyBehavior.NOT_APPLICABLE)


@pytest.mark.parametrize("field", ["expected_effects", "completion_evidence"])
def test_write_requires_effect_and_evidence(field: str) -> None:
    """Every write declares both expected state and completion evidence."""
    with pytest.raises(ValidationError, match="expected effects and completion evidence"):
        make_capability(**{field: ()})


def test_capability_cannot_compensate_itself() -> None:
    """Compensation must name a distinct capability."""
    with pytest.raises(ValidationError, match="cannot compensate itself"):
        make_capability(compensation_capability_id="device.prepare")


def test_live_bounded_rejects_r2() -> None:
    """Only R0 and R1 contracts may declare future live-bounded support."""
    with pytest.raises(ValidationError, match="only R0 and R1"):
        make_capability(
            risk_class=RiskClass.R2,
            authorization=AuthorizationRequirement.APPROVAL,
            supported_modes=frozenset({AutonomyMode.LIVE_BOUNDED}),
        )


def test_r1_contract_can_declare_distinct_compensation() -> None:
    """A valid R1 write may reference a distinct compensation contract."""
    capability = make_capability(
        parameters=(make_parameter(),),
        preconditions=(make_condition(condition_id="condition.safe"),),
        compensation_capability_id="device.reset",
        supported_modes=frozenset({AutonomyMode.SIMULATION, AutonomyMode.LIVE_BOUNDED}),
    )
    assert capability.compensation_capability_id == "device.reset"
