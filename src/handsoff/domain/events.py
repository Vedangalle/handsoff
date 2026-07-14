"""Append-only operational-ledger event contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar, Self

from pydantic import Field, model_validator

from handsoff.domain import ContractModel, Identifier, NonEmptyText, UtcDateTime
from handsoff.domain.execution import (
    ActionTransition,
    PlanTransition,
    VerificationResult,
)
from handsoff.domain.goals import Goal
from handsoff.domain.observations import Observation
from handsoff.domain.plans import PlanProposal
from handsoff.domain.policies import Approval, PolicyEvaluation


class EventKind(StrEnum):
    """Required operational evidence categories."""

    GOAL_RECEIVED = "goal_received"
    OBSERVATION_RECORDED = "observation_recorded"
    PLAN_PROPOSED = "plan_proposed"
    POLICY_EVALUATED = "policy_evaluated"
    APPROVAL_RECORDED = "approval_recorded"
    PLAN_TRANSITIONED = "plan_transitioned"
    ACTION_TRANSITIONED = "action_transitioned"
    VERIFICATION_RECORDED = "verification_recorded"
    FAILURE_RECORDED = "failure_recorded"


class FailureRecord(ContractModel):
    """Non-secret structured failure evidence."""

    failure_code: Identifier
    summary: NonEmptyText
    retryable: bool
    subject_id: Identifier


EventPayload = (
    Goal
    | Observation
    | PlanProposal
    | PolicyEvaluation
    | Approval
    | PlanTransition
    | ActionTransition
    | VerificationResult
    | FailureRecord
)


class LedgerEvent(ContractModel):
    """Sequenced event envelope with a kind-bound domain payload."""

    PAYLOAD_TYPES: ClassVar[dict[EventKind, type[ContractModel]]] = {
        EventKind.GOAL_RECEIVED: Goal,
        EventKind.OBSERVATION_RECORDED: Observation,
        EventKind.PLAN_PROPOSED: PlanProposal,
        EventKind.POLICY_EVALUATED: PolicyEvaluation,
        EventKind.APPROVAL_RECORDED: Approval,
        EventKind.PLAN_TRANSITIONED: PlanTransition,
        EventKind.ACTION_TRANSITIONED: ActionTransition,
        EventKind.VERIFICATION_RECORDED: VerificationResult,
        EventKind.FAILURE_RECORDED: FailureRecord,
    }

    event_id: Identifier
    stream_id: Identifier
    sequence_number: Annotated[int, Field(ge=1)]
    kind: EventKind
    occurred_at: UtcDateTime
    correlation_id: Identifier
    causation_event_id: Identifier | None = None
    payload: EventPayload

    @model_validator(mode="after")
    def validate_event(self) -> Self:
        """Prevent self-causation and event-kind/payload contradictions."""
        if self.causation_event_id == self.event_id:
            message = "an event cannot cause itself"
            raise ValueError(message)
        expected_type = self.PAYLOAD_TYPES[self.kind]
        if not isinstance(self.payload, expected_type):
            message = "event payload type does not match event kind"
            raise ValueError(message)  # noqa: TRY004
        return self


__all__ = ["EventKind", "FailureRecord", "LedgerEvent"]
