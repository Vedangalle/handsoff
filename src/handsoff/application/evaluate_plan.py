"""Deterministic, model-independent authorization policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from handsoff.application.conditions import ConditionEvaluator
from handsoff.domain.capabilities import AuthorizationRequirement, RiskClass
from handsoff.domain.goals import AcceptanceCondition, ConditionOperator
from handsoff.domain.policies import (
    ActionPolicyDecision,
    PolicyDecision,
    PolicyEvaluation,
)

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.application.capability_registry import CapabilityRegistry
    from handsoff.application.world_model import WorldModel
    from handsoff.domain.plans import PlannedAction, PlanProposal


@dataclass(frozen=True, slots=True)
class CapabilityObservationRule:
    """A deterministic observation rule bound to one capability."""

    capability_id: str
    condition: AcceptanceCondition


ARRIVAL_CONFIDENCE_RULE = CapabilityObservationRule(
    capability_id="garage.open",
    condition=AcceptanceCondition(
        condition_id="policy.destination-confidence",
        description="Destination confidence must be at least 0.8",
        entity_id="vehicle.primary",
        property_id="destination_confidence",
        operator=ConditionOperator.GREATER_THAN_OR_EQUAL,
        target_value=0.8,
        unit="ratio",
    ),
)


class PolicyKernel:
    """Evaluate pure plan, capability, and observation data."""

    policy_version = "1.0.0"

    def __init__(
        self,
        registry: CapabilityRegistry,
        world: WorldModel,
        rules: tuple[CapabilityObservationRule, ...] = (ARRIVAL_CONFIDENCE_RULE,),
    ) -> None:
        """Bind deterministic state, capability declarations, and policy rules."""
        self._registry = registry
        self._world = world
        self._rules = rules
        self._conditions = ConditionEvaluator()

    def evaluate(self, plan: PlanProposal, now: datetime) -> PolicyEvaluation:
        """Return a reproducible aggregate decision for every proposed action."""
        inputs = {plan.plan_id}
        action_decisions = tuple(
            self._evaluate_action(action, plan, now, inputs) for action in plan.actions
        )
        decisions = {result.decision for result in action_decisions}
        decision = PolicyDecision.ALLOW
        if PolicyDecision.DENY in decisions:
            decision = PolicyDecision.DENY
        elif PolicyDecision.REQUIRE_APPROVAL in decisions:
            decision = PolicyDecision.REQUIRE_APPROVAL
        reason_by_decision = {
            PolicyDecision.ALLOW: "All proposed actions satisfy deterministic policy",
            PolicyDecision.REQUIRE_APPROVAL: "At least one action requires explicit approval",
            PolicyDecision.DENY: "At least one action violates deterministic policy",
        }
        return PolicyEvaluation(
            evaluation_id=plan.plan_id.replace("plan.", "policy-evaluation.", 1),
            plan_id=plan.plan_id,
            policy_version=self.policy_version,
            decision=decision,
            reasons=(reason_by_decision[decision],),
            inputs_considered=tuple(sorted(inputs)),
            action_decisions=action_decisions,
            evaluated_at=now,
        )

    def _evaluate_action(
        self,
        action: PlannedAction,
        plan: PlanProposal,
        now: datetime,
        inputs: set[str],
    ) -> ActionPolicyDecision:
        """Evaluate one action and accumulate immutable evidence identifiers."""
        capability = self._registry.resolve(action.capability_id, action.capability_version)
        inputs.add(action.capability_id)
        if capability is None:
            return self._decision(
                action,
                RiskClass.R3,
                PolicyDecision.DENY,
                ("Capability identifier or version is not allowlisted",),
            )

        reasons = list(self._registry.validate_action(action, plan.mode))
        if now >= plan.expires_at:
            reasons.append("Plan has expired")
        if capability.risk_class is RiskClass.R3:
            reasons.append("R3 capabilities are prohibited")
        if capability.authorization is AuthorizationRequirement.PROHIBITED:
            reasons.append("Capability authorization is prohibited")

        conditions = self._conditions_for(action, capability.preconditions)
        for condition in conditions:
            check = self._conditions.evaluate(condition, self._world, now)
            inputs.update(check.observation_ids)
            if not check.satisfied:
                reasons.append(f"{condition.condition_id}: {check.reason}")

        if reasons:
            return self._decision(
                action,
                capability.risk_class,
                PolicyDecision.DENY,
                tuple(reasons),
            )
        if capability.authorization is AuthorizationRequirement.APPROVAL:
            return self._decision(
                action,
                capability.risk_class,
                PolicyDecision.REQUIRE_APPROVAL,
                ("Capability requires explicit human approval",),
            )
        return self._decision(
            action,
            capability.risk_class,
            PolicyDecision.ALLOW,
            ("Capability satisfies deterministic policy",),
        )

    def _conditions_for(
        self,
        action: PlannedAction,
        capability_conditions: tuple[AcceptanceCondition, ...],
    ) -> tuple[AcceptanceCondition, ...]:
        """Combine action, capability, and global rules without duplicate IDs."""
        combined = (*capability_conditions, *action.preconditions)
        combined += tuple(
            rule.condition for rule in self._rules if rule.capability_id == action.capability_id
        )
        by_id = {condition.condition_id: condition for condition in combined}
        return tuple(by_id[key] for key in sorted(by_id))

    @staticmethod
    def _decision(
        action: PlannedAction,
        risk_class: RiskClass,
        decision: PolicyDecision,
        reasons: tuple[str, ...],
    ) -> ActionPolicyDecision:
        return ActionPolicyDecision(
            action_id=action.action_id,
            risk_class=risk_class,
            decision=decision,
            reasons=reasons,
        )


__all__ = ["ARRIVAL_CONFIDENCE_RULE", "CapabilityObservationRule", "PolicyKernel"]
