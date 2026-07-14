"""Goal and acceptance-condition contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from handsoff.domain import ContractModel, Identifier, NonEmptyText, UtcDateTime


class ConditionOperator(StrEnum):
    """Supported deterministic acceptance-condition operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    WITHIN = "within"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class AcceptanceCondition(ContractModel):
    """A machine-evaluable condition over one normalized observation."""

    condition_id: Identifier
    description: NonEmptyText
    entity_id: Identifier
    property_id: Identifier
    operator: ConditionOperator
    target_value: JsonValue | None = None
    unit: NonEmptyText | None = None
    tolerance: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def validate_operator_arguments(self) -> Self:
        """Require exactly the arguments needed by the selected operator."""
        truth_operators = {ConditionOperator.IS_TRUE, ConditionOperator.IS_FALSE}
        if self.operator in truth_operators:
            if self.target_value is not None or self.unit is not None or self.tolerance is not None:
                message = "truth operators do not accept target, unit, or tolerance"
                raise ValueError(message)
            return self

        if self.target_value is None:
            message = "comparison operators require target_value"
            raise ValueError(message)

        if self.operator is ConditionOperator.WITHIN:
            if (
                isinstance(self.target_value, bool)
                or not isinstance(self.target_value, (int, float))
                or self.tolerance is None
            ):
                message = "within requires a numeric target and tolerance"
                raise ValueError(message)
            return self

        if self.tolerance is not None:
            message = "tolerance is valid only for the within operator"
            raise ValueError(message)
        return self


class Goal(ContractModel):
    """A user objective with explicit, deterministic acceptance conditions."""

    goal_id: Identifier
    objective: NonEmptyText
    requested_at: UtcDateTime
    deadline: UtcDateTime | None = None
    acceptance_conditions: Annotated[tuple[AcceptanceCondition, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_goal(self) -> Self:
        """Require unique conditions and a deadline after the request time."""
        condition_ids = [condition.condition_id for condition in self.acceptance_conditions]
        if len(condition_ids) != len(set(condition_ids)):
            message = "acceptance condition identifiers must be unique"
            raise ValueError(message)
        if self.deadline is not None and self.deadline <= self.requested_at:
            message = "deadline must be later than requested_at"
            raise ValueError(message)
        return self


__all__ = ["AcceptanceCondition", "ConditionOperator", "Goal"]
