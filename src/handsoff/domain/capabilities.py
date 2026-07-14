"""Typed capability-contract vocabulary."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from handsoff.domain import ContractModel, ContractVersion, Identifier, NonEmptyText
from handsoff.domain.goals import AcceptanceCondition  # noqa: TC001


class AutonomyMode(StrEnum):
    """Explicit runtime authority modes."""

    SIMULATION = "simulation"
    SHADOW = "shadow"
    SUPERVISED = "supervised"
    LIVE_BOUNDED = "live_bounded"


class OperationClass(StrEnum):
    """Whether a capability observes or attempts to change state."""

    READ = "read"
    WRITE = "write"


class RiskClass(StrEnum):
    """Prototype risk classification."""

    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class AuthorizationRequirement(StrEnum):
    """Authority required before a capability may be dispatched."""

    NONE = "none"
    APPROVAL = "approval"
    PROHIBITED = "prohibited"


class IdempotencyBehavior(StrEnum):
    """How duplicate effects are prevented."""

    NOT_APPLICABLE = "not_applicable"
    KEY_REQUIRED = "key_required"
    INHERENT = "inherent"


class ParameterType(StrEnum):
    """JSON-compatible parameter value types."""

    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"


class CapabilityParameter(ContractModel):
    """One named parameter in a capability contract."""

    name: Identifier
    value_type: ParameterType
    description: NonEmptyText
    required: bool
    unit: NonEmptyText | None = None
    minimum: Annotated[float, Field(allow_inf_nan=False)] | None = None
    maximum: Annotated[float, Field(allow_inf_nan=False)] | None = None
    allowed_values: tuple[bool | int | float | str, ...] = ()

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        """Restrict numeric bounds to numeric parameters and order them."""
        has_bounds = self.minimum is not None or self.maximum is not None
        if has_bounds and self.value_type not in {ParameterType.INTEGER, ParameterType.NUMBER}:
            message = "minimum and maximum are valid only for numeric parameters"
            raise ValueError(message)
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            message = "minimum cannot exceed maximum"
            raise ValueError(message)
        self._validate_allowed_values()
        return self

    def _validate_allowed_values(self) -> None:
        """Ensure enumerated values agree with the parameter declaration."""
        if len(self.allowed_values) != len(set(self.allowed_values)):
            message = "allowed parameter values must be unique"
            raise ValueError(message)
        for value in self.allowed_values:
            if not self._matches_declared_type(value):
                message = "allowed parameter value does not match value_type"
                raise ValueError(message)
            if isinstance(value, float) and not math.isfinite(value):
                message = "allowed numeric parameter values must be finite"
                raise ValueError(message)
            if (
                self.minimum is not None
                and isinstance(value, (int, float))
                and value < self.minimum
            ):
                message = "allowed parameter value is below minimum"
                raise ValueError(message)
            if (
                self.maximum is not None
                and isinstance(value, (int, float))
                and value > self.maximum
            ):
                message = "allowed parameter value is above maximum"
                raise ValueError(message)

    def _matches_declared_type(self, value: object) -> bool:
        """Check an allowed scalar without Python's Boolean-as-integer ambiguity."""
        if self.value_type is ParameterType.BOOLEAN:
            return type(value) is bool
        if self.value_type is ParameterType.INTEGER:
            return type(value) is int
        if self.value_type is ParameterType.NUMBER:
            return type(value) in {int, float}
        return isinstance(value, str)


class CapabilityContract(ContractModel):
    """A bounded, versioned adapter capability declaration."""

    capability_id: Identifier
    version: ContractVersion
    adapter_id: Identifier
    target_entity_id: Identifier
    description: NonEmptyText
    operation: OperationClass
    risk_class: RiskClass
    authorization: AuthorizationRequirement
    parameters: tuple[CapabilityParameter, ...] = ()
    preconditions: tuple[AcceptanceCondition, ...] = ()
    expected_effects: tuple[AcceptanceCondition, ...] = ()
    completion_evidence: tuple[AcceptanceCondition, ...] = ()
    timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    max_attempts: Annotated[int, Field(ge=1)]
    idempotency: IdempotencyBehavior
    compensation_capability_id: Identifier | None = None
    supported_modes: frozenset[AutonomyMode] = frozenset()

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        """Enforce risk, authority, idempotency, and evidence invariants."""
        self._validate_parameters()
        self._validate_risk_and_authority()
        self._validate_write_evidence()
        self._validate_compensation_and_modes()
        return self

    def _validate_parameters(self) -> None:
        """Require parameter names to be unique within the contract."""
        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            message = "capability parameter names must be unique"
            raise ValueError(message)
        for conditions, label in (
            (self.preconditions, "precondition"),
            (self.expected_effects, "expected effect"),
            (self.completion_evidence, "completion evidence"),
        ):
            condition_ids = [condition.condition_id for condition in conditions]
            if len(condition_ids) != len(set(condition_ids)):
                message = f"{label} identifiers must be unique"
                raise ValueError(message)

    def _validate_risk_and_authority(self) -> None:
        """Enforce risk-class authorization boundaries."""
        if self.risk_class is RiskClass.R0:
            if self.operation is not OperationClass.READ:
                message = "R0 capabilities must be read-only"
                raise ValueError(message)
            if self.authorization is not AuthorizationRequirement.NONE:
                message = "R0 capabilities cannot require action authorization"
                raise ValueError(message)

        if (
            self.risk_class is RiskClass.R2
            and self.authorization is AuthorizationRequirement.NONE
            and not self.supported_modes <= {AutonomyMode.SIMULATION}
        ):
            message = "R2 capabilities require approval or prohibition outside simulation"
            raise ValueError(message)

        if self.risk_class is RiskClass.R3:
            if self.authorization is not AuthorizationRequirement.PROHIBITED:
                message = "R3 capabilities must be prohibited"
                raise ValueError(message)
            if self.supported_modes:
                message = "R3 capabilities cannot support a prototype autonomy mode"
                raise ValueError(message)

    def _validate_write_evidence(self) -> None:
        """Require duplicate protection and evidence for write capabilities."""
        if self.operation is OperationClass.WRITE:
            if self.idempotency is IdempotencyBehavior.NOT_APPLICABLE:
                message = "write capabilities require explicit idempotency behavior"
                raise ValueError(message)
            if not self.expected_effects or not self.completion_evidence:
                message = "write capabilities require expected effects and completion evidence"
                raise ValueError(message)

    def _validate_compensation_and_modes(self) -> None:
        """Prevent self-compensation and high-risk live-bounded contracts."""
        if self.compensation_capability_id == self.capability_id:
            message = "a capability cannot compensate itself"
            raise ValueError(message)

        if AutonomyMode.LIVE_BOUNDED in self.supported_modes and self.risk_class not in {
            RiskClass.R0,
            RiskClass.R1,
        }:
            message = "live-bounded mode supports only R0 and R1 capabilities"
            raise ValueError(message)


__all__ = [
    "AuthorizationRequirement",
    "AutonomyMode",
    "CapabilityContract",
    "CapabilityParameter",
    "IdempotencyBehavior",
    "OperationClass",
    "ParameterType",
    "RiskClass",
]
