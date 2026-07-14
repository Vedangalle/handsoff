"""Planner-evaluation evidence contracts."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from handsoff.domain import ContractModel, ContractVersion, Identifier, NonEmptyText, UtcDateTime
from handsoff.domain.policies import PolicyDecision  # noqa: TC001 - Pydantic runtime field


class PlannerEvaluationRecord(ContractModel):
    """Observed quality metrics for one fixed planner configuration."""

    evaluation_id: Identifier
    scenario_id: Identifier
    provider: NonEmptyText
    model: NonEmptyText
    prompt_version: ContractVersion
    schema_version: ContractVersion
    temperature: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    evaluated_at: UtcDateTime
    schema_valid: bool
    capability_hallucination_count: Annotated[int, Field(ge=0)]
    invalid_parameter_action_count: Annotated[int, Field(ge=0)]
    missing_precondition_action_count: Annotated[int, Field(ge=0)]
    policy_decision: PolicyDecision | None
    latency_ms: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    failure_reason: NonEmptyText | None = None


__all__ = ["PlannerEvaluationRecord"]
