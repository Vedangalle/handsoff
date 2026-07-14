"""Allowlisted capability lookup and planned-parameter validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from handsoff.domain.capabilities import (
    AutonomyMode,
    CapabilityContract,
    CapabilityParameter,
    ParameterType,
)

if TYPE_CHECKING:
    from pydantic import JsonValue

    from handsoff.domain.plans import PlannedAction


def _is_number(value: object) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float))


class CapabilityRegistry:
    """Immutable-by-interface registry of declared capability versions."""

    def __init__(self, capabilities: tuple[CapabilityContract, ...]) -> None:
        """Index exact capability versions and reject duplicates."""
        self._contracts: dict[tuple[str, str], CapabilityContract] = {}
        for capability in capabilities:
            key = (capability.capability_id, capability.version)
            if key in self._contracts:
                message = "capability version is declared more than once"
                raise ValueError(message)
            self._contracts[key] = capability

    def resolve(self, capability_id: str, version: str) -> CapabilityContract | None:
        """Resolve one exact, allowlisted capability version."""
        return self._contracts.get((capability_id, version))

    def contracts(self) -> tuple[CapabilityContract, ...]:
        """Return declarations in stable identifier/version order."""
        return tuple(self._contracts[key] for key in sorted(self._contracts))

    def validate_action(self, action: PlannedAction, mode: AutonomyMode) -> tuple[str, ...]:
        """Return every capability-contract violation for an untrusted action."""
        capability = self.resolve(action.capability_id, action.capability_version)
        if capability is None:
            return ("capability identifier or version is not declared",)

        errors: list[str] = []
        if action.target_entity_id != capability.target_entity_id:
            errors.append("action target does not match capability target")
        if mode not in capability.supported_modes:
            errors.append("capability does not support the configured autonomy mode")

        declared = {parameter.name: parameter for parameter in capability.parameters}
        supplied = set(action.parameters)
        required = {parameter.name for parameter in capability.parameters if parameter.required}
        if missing := required - supplied:
            errors.append(f"required parameters are missing: {', '.join(sorted(missing))}")
        if unknown := supplied - set(declared):
            errors.append(f"undeclared parameters were supplied: {', '.join(sorted(unknown))}")
        for name in sorted(supplied & set(declared)):
            error = self._validate_parameter(declared[name], action.parameters[name])
            if error is not None:
                errors.append(f"parameter {name}: {error}")
        return tuple(errors)

    @staticmethod
    def _validate_parameter(parameter: CapabilityParameter, value: JsonValue) -> str | None:
        """Validate one JSON value without permissive type coercion."""
        type_matches = {
            ParameterType.BOOLEAN: type(value) is bool,
            ParameterType.INTEGER: type(value) is int,
            ParameterType.NUMBER: _is_number(value),
            ParameterType.STRING: isinstance(value, str),
        }
        if not type_matches[parameter.value_type]:
            return "value type does not match the declaration"
        if parameter.allowed_values and value not in parameter.allowed_values:
            return "value is outside the declared allowlist"
        if _is_number(value):
            if parameter.minimum is not None and value < parameter.minimum:
                return "value is below the declared minimum"
            if parameter.maximum is not None and value > parameter.maximum:
                return "value is above the declared maximum"
        return None


__all__ = ["CapabilityRegistry"]
