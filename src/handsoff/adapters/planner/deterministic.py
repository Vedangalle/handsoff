"""Offline deterministic planner used by tests, replay, and provider fallback."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from handsoff.domain.plans import FailureStrategy, PlannedAction, PlanProposal
from handsoff.ports.planner import PlannerRequest, PlannerResult

if TYPE_CHECKING:
    from pydantic import JsonValue

    from handsoff.domain.capabilities import CapabilityContract, CapabilityParameter
    from handsoff.domain.goals import AcceptanceCondition


class DeterministicPlanner:
    """Compile declared capabilities into a stable plan without a model."""

    planner_id = "planner.fixture"
    planner_version = "1.0.0"

    def propose(self, request: PlannerRequest) -> PlannerResult:
        """Build a plan exclusively from trusted contracts."""
        plan_id = request.goal.goal_id.replace("goal.", "plan.", 1)
        expires_at = request.now + timedelta(minutes=1)
        if request.goal.deadline is not None:
            expires_at = min(expires_at, request.goal.deadline)
        actions = tuple(
            self._build_action(plan_id, capability, request.goal.acceptance_conditions)
            for capability in sorted(request.capabilities, key=lambda item: item.capability_id)
        )
        plan = PlanProposal(
            plan_id=plan_id,
            schema_version="1.0.0",
            goal_id=request.goal.goal_id,
            created_at=request.now,
            expires_at=expires_at,
            mode=request.mode,
            planner_id=self.planner_id,
            planner_version=self.planner_version,
            world_state_observation_ids=tuple(
                sorted(observation.observation_id for observation in request.observations)
            ),
            actions=actions,
        )
        return PlannerResult(
            plan=plan,
            provider="deterministic",
            model=self.planner_id,
            used_fallback=False,
            latency_ms=0.0,
        )

    def _build_action(
        self,
        plan_id: str,
        capability: CapabilityContract,
        goal_conditions: tuple[AcceptanceCondition, ...],
    ) -> PlannedAction:
        """Map one capability to its matching goal evidence."""
        matching = tuple(
            condition
            for condition in goal_conditions
            if any(
                condition.entity_id == effect.entity_id
                and condition.property_id == effect.property_id
                for effect in capability.expected_effects
            )
        )
        conditions = matching or capability.expected_effects
        parameters = {
            parameter.name: self._infer_parameter(parameter, capability)
            for parameter in capability.parameters
            if parameter.required
        }
        suffix = capability.capability_id.replace(".", "-")
        return PlannedAction(
            action_id=f"action.{suffix}",
            capability_id=capability.capability_id,
            capability_version=capability.version,
            target_entity_id=capability.target_entity_id,
            parameters=parameters,
            preconditions=capability.preconditions,
            acceptance_conditions=conditions,
            idempotency_key=f"{plan_id}.{suffix}",
            on_failure=FailureStrategy.CONTINUE,
        )

    @staticmethod
    def _infer_parameter(
        parameter: CapabilityParameter,
        capability: CapabilityContract,
    ) -> JsonValue:
        """Infer a required parameter only from a declared expected effect."""
        if parameter.allowed_values:
            return parameter.allowed_values[0]
        for effect in capability.expected_effects:
            target = effect.target_value
            if target is not None and (parameter.unit is None or parameter.unit == effect.unit):
                return target
        message = f"cannot infer required parameter {parameter.name} from capability effects"
        raise ValueError(message)


__all__ = ["DeterministicPlanner"]
