"""Execution-state and verification-result contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar, Self

from pydantic import Field, model_validator

from handsoff.domain import ContractModel, Identifier, NonEmptyText, UtcDateTime


class PlanState(StrEnum):
    """Plan lifecycle states."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    POLICY_EVALUATED = "policy_evaluated"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    COMPENSATED = "compensated"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionState(StrEnum):
    """Action lifecycle states."""

    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    DISPATCHED = "dispatched"
    ADAPTER_ACCEPTED = "adapter_accepted"
    EFFECT_OBSERVED = "effect_observed"
    VERIFIED = "verified"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    COMPENSATED = "compensated"


class PlanTransition(ContractModel):
    """One legal plan-state transition record."""

    LEGAL_TRANSITIONS: ClassVar[dict[PlanState, frozenset[PlanState]]] = {
        PlanState.PROPOSED: frozenset({PlanState.VALIDATED, PlanState.REJECTED, PlanState.EXPIRED}),
        PlanState.VALIDATED: frozenset(
            {PlanState.POLICY_EVALUATED, PlanState.REJECTED, PlanState.EXPIRED}
        ),
        PlanState.POLICY_EVALUATED: frozenset(
            {
                PlanState.AWAITING_APPROVAL,
                PlanState.APPROVED,
                PlanState.REJECTED,
                PlanState.EXPIRED,
            }
        ),
        PlanState.AWAITING_APPROVAL: frozenset(
            {PlanState.APPROVED, PlanState.REJECTED, PlanState.EXPIRED}
        ),
        PlanState.APPROVED: frozenset({PlanState.EXECUTING, PlanState.REJECTED, PlanState.EXPIRED}),
        PlanState.EXECUTING: frozenset({PlanState.VERIFYING}),
        PlanState.VERIFYING: frozenset(
            {
                PlanState.SUCCEEDED,
                PlanState.PARTIALLY_SUCCEEDED,
                PlanState.FAILED,
                PlanState.COMPENSATED,
            }
        ),
    }

    plan_id: Identifier
    from_state: PlanState
    to_state: PlanState
    occurred_at: UtcDateTime
    reason: NonEmptyText

    @model_validator(mode="after")
    def validate_transition(self) -> Self:
        """Reject transitions not present in the approved lifecycle graph."""
        if self.to_state not in self.LEGAL_TRANSITIONS.get(self.from_state, frozenset()):
            message = "illegal plan state transition"
            raise ValueError(message)
        return self


class ActionTransition(ContractModel):
    """One legal action-state transition record."""

    LEGAL_TRANSITIONS: ClassVar[dict[ActionState, frozenset[ActionState]]] = {
        ActionState.PROPOSED: frozenset({ActionState.AUTHORIZED}),
        ActionState.AUTHORIZED: frozenset(
            {ActionState.DISPATCHED, ActionState.FAILED, ActionState.TIMED_OUT}
        ),
        ActionState.DISPATCHED: frozenset(
            {ActionState.ADAPTER_ACCEPTED, ActionState.FAILED, ActionState.TIMED_OUT}
        ),
        ActionState.ADAPTER_ACCEPTED: frozenset(
            {ActionState.EFFECT_OBSERVED, ActionState.FAILED, ActionState.TIMED_OUT}
        ),
        ActionState.EFFECT_OBSERVED: frozenset(
            {ActionState.VERIFIED, ActionState.FAILED, ActionState.TIMED_OUT}
        ),
        ActionState.VERIFIED: frozenset({ActionState.COMPENSATED}),
        ActionState.FAILED: frozenset({ActionState.COMPENSATED}),
        ActionState.TIMED_OUT: frozenset({ActionState.COMPENSATED}),
    }

    action_id: Identifier
    from_state: ActionState
    to_state: ActionState
    occurred_at: UtcDateTime
    reason: NonEmptyText

    @model_validator(mode="after")
    def validate_transition(self) -> Self:
        """Reject transitions that bypass authorization or evidence states."""
        if self.to_state not in self.LEGAL_TRANSITIONS.get(self.from_state, frozenset()):
            message = "illegal action state transition"
            raise ValueError(message)
        return self


class VerificationResult(ContractModel):
    """Evaluation of one acceptance condition against observed state."""

    condition_id: Identifier
    satisfied: bool
    observation_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    evaluated_at: UtcDateTime
    reason: NonEmptyText

    @model_validator(mode="after")
    def validate_observation_ids(self) -> Self:
        """Require each evidence observation to appear once."""
        if len(self.observation_ids) != len(set(self.observation_ids)):
            message = "verification observation identifiers must be unique"
            raise ValueError(message)
        return self


__all__ = [
    "ActionState",
    "ActionTransition",
    "PlanState",
    "PlanTransition",
    "VerificationResult",
]
