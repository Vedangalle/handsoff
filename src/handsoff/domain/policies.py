"""Deterministic policy-result and approval contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from handsoff.domain import ContractModel, ContractVersion, Identifier, NonEmptyText, UtcDateTime
from handsoff.domain.capabilities import RiskClass


class PolicyDecision(StrEnum):
    """Exhaustive policy outcomes."""

    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ALLOW = "allow"


class ActionPolicyDecision(ContractModel):
    """Policy outcome for one proposed action."""

    action_id: Identifier
    risk_class: RiskClass
    decision: PolicyDecision
    reasons: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def prohibit_r3(self) -> Self:
        """Make every non-denial R3 result schema-invalid."""
        if self.risk_class is RiskClass.R3 and self.decision is not PolicyDecision.DENY:
            message = "R3 action policy decisions must be deny"
            raise ValueError(message)
        return self


class PolicyEvaluation(ContractModel):
    """Versioned, reproducible policy result for a proposed plan."""

    evaluation_id: Identifier
    plan_id: Identifier
    policy_version: ContractVersion
    decision: PolicyDecision
    reasons: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    inputs_considered: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    action_decisions: Annotated[tuple[ActionPolicyDecision, ...], Field(min_length=1)]
    evaluated_at: UtcDateTime

    @model_validator(mode="after")
    def validate_aggregate_decision(self) -> Self:
        """Require the plan decision to agree with all action decisions."""
        action_ids = [result.action_id for result in self.action_decisions]
        if len(action_ids) != len(set(action_ids)):
            message = "action policy decision identifiers must be unique"
            raise ValueError(message)
        if len(self.inputs_considered) != len(set(self.inputs_considered)):
            message = "policy input identifiers must be unique"
            raise ValueError(message)

        decisions = {result.decision for result in self.action_decisions}
        expected = PolicyDecision.ALLOW
        if PolicyDecision.DENY in decisions:
            expected = PolicyDecision.DENY
        elif PolicyDecision.REQUIRE_APPROVAL in decisions:
            expected = PolicyDecision.REQUIRE_APPROVAL
        if self.decision is not expected:
            message = "plan policy decision must aggregate action decisions"
            raise ValueError(message)
        return self


class Approval(ContractModel):
    """Time-bounded human authorization tied to one policy evaluation."""

    approval_id: Identifier
    plan_id: Identifier
    policy_evaluation_id: Identifier
    approver_id: Identifier
    approved_action_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    issued_at: UtcDateTime
    expires_at: UtcDateTime

    @model_validator(mode="after")
    def validate_approval(self) -> Self:
        """Require a future expiration and unique authorized actions."""
        if self.expires_at <= self.issued_at:
            message = "approval expiration must be later than issue time"
            raise ValueError(message)
        if len(self.approved_action_ids) != len(set(self.approved_action_ids)):
            message = "approved action identifiers must be unique"
            raise ValueError(message)
        return self


__all__ = ["ActionPolicyDecision", "Approval", "PolicyDecision", "PolicyEvaluation"]
