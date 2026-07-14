"""Deterministic factories for domain-contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from handsoff.domain.capabilities import (
    AuthorizationRequirement,
    AutonomyMode,
    CapabilityContract,
    IdempotencyBehavior,
    OperationClass,
    RiskClass,
)
from handsoff.domain.execution import PlanState
from handsoff.domain.goals import AcceptanceCondition, ConditionOperator, Goal
from handsoff.domain.observations import Observation, ObservationQuality
from handsoff.domain.plans import FailureStrategy, PlannedAction, PlanProposal
from handsoff.domain.policies import ActionPolicyDecision, PolicyDecision, PolicyEvaluation
from handsoff.domain.scenarios import ScenarioDefinition, ScenarioExpectation

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


def make_condition(**overrides: object) -> AcceptanceCondition:
    """Build a valid equality condition."""
    values: dict[str, object] = {
        "condition_id": "condition.ready",
        "description": "Target state is ready",
        "entity_id": "device.primary",
        "property_id": "state",
        "operator": ConditionOperator.EQUALS,
        "target_value": "ready",
    }
    values.update(overrides)
    return AcceptanceCondition.model_validate(values)


def make_goal(**overrides: object) -> Goal:
    """Build a valid goal at the deterministic reference time."""
    values: dict[str, object] = {
        "goal_id": "goal.arrival",
        "objective": "Prepare the simulated environment for arrival",
        "requested_at": NOW,
        "deadline": NOW + timedelta(minutes=5),
        "acceptance_conditions": (make_condition(),),
    }
    values.update(overrides)
    return Goal.model_validate(values)


def make_observation(**overrides: object) -> Observation:
    """Build a valid nominal simulated observation."""
    values: dict[str, object] = {
        "observation_id": "observation.initial",
        "entity_id": "device.primary",
        "property_id": "state",
        "value": "idle",
        "source_adapter_id": "adapter.simulator",
        "observed_at": NOW,
        "freshness_limit_seconds": 30.0,
        "confidence": 1.0,
        "quality": ObservationQuality.NOMINAL,
        "correlation_id": "correlation.arrival",
    }
    values.update(overrides)
    return Observation.model_validate(values)


def make_capability(**overrides: object) -> CapabilityContract:
    """Build a valid R1 simulated write capability."""
    effect = make_condition()
    values: dict[str, object] = {
        "capability_id": "device.prepare",
        "version": "1.0.0",
        "adapter_id": "adapter.simulator",
        "target_entity_id": "device.primary",
        "description": "Prepare a simulated device",
        "operation": OperationClass.WRITE,
        "risk_class": RiskClass.R1,
        "authorization": AuthorizationRequirement.NONE,
        "expected_effects": (effect,),
        "completion_evidence": (effect,),
        "timeout_seconds": 5.0,
        "max_attempts": 1,
        "idempotency": IdempotencyBehavior.KEY_REQUIRED,
        "supported_modes": frozenset({AutonomyMode.SIMULATION}),
    }
    values.update(overrides)
    return CapabilityContract.model_validate(values)


def make_action(**overrides: object) -> PlannedAction:
    """Build a valid planned action."""
    values: dict[str, object] = {
        "action_id": "action.prepare",
        "capability_id": "device.prepare",
        "capability_version": "1.0.0",
        "target_entity_id": "device.primary",
        "parameters": {},
        "acceptance_conditions": (make_condition(),),
        "idempotency_key": "idempotency.prepare",
        "on_failure": FailureStrategy.STOP,
    }
    values.update(overrides)
    return PlannedAction.model_validate(values)


def make_plan(**overrides: object) -> PlanProposal:
    """Build a valid single-action plan proposal."""
    values: dict[str, object] = {
        "plan_id": "plan.arrival",
        "schema_version": "1.0.0",
        "goal_id": "goal.arrival",
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=1),
        "mode": AutonomyMode.SIMULATION,
        "planner_id": "planner.fixture",
        "planner_version": "1.0.0",
        "world_state_observation_ids": ("observation.initial",),
        "actions": (make_action(),),
    }
    values.update(overrides)
    return PlanProposal.model_validate(values)


def make_action_decision(**overrides: object) -> ActionPolicyDecision:
    """Build a valid allowed R1 action decision."""
    values: dict[str, object] = {
        "action_id": "action.prepare",
        "risk_class": RiskClass.R1,
        "decision": PolicyDecision.ALLOW,
        "reasons": ("Simulation-only R1 capability is permitted",),
    }
    values.update(overrides)
    return ActionPolicyDecision.model_validate(values)


def make_policy_evaluation(**overrides: object) -> PolicyEvaluation:
    """Build a valid allowed policy evaluation."""
    values: dict[str, object] = {
        "evaluation_id": "policy-evaluation.arrival",
        "plan_id": "plan.arrival",
        "policy_version": "1.0.0",
        "decision": PolicyDecision.ALLOW,
        "reasons": ("All proposed actions are allowed in simulation",),
        "inputs_considered": ("observation.initial", "capability.device-prepare"),
        "action_decisions": (make_action_decision(),),
        "evaluated_at": NOW,
    }
    values.update(overrides)
    return PolicyEvaluation.model_validate(values)


def make_scenario(**overrides: object) -> ScenarioDefinition:
    """Build a minimal valid simulation scenario."""
    values: dict[str, object] = {
        "schema_version": "1.0.0",
        "scenario_id": "scenario.nominal",
        "title": "Nominal simulated scenario",
        "description": "All simulated actions produce their declared effects.",
        "simulation_only": True,
        "clock_start_at": NOW,
        "goal": make_goal(),
        "capabilities": (make_capability(),),
        "initial_observations": (make_observation(),),
        "expected": ScenarioExpectation(
            policy_decision=PolicyDecision.ALLOW,
            terminal_plan_state=PlanState.SUCCEEDED,
            dispatched_capability_ids=("device.prepare",),
            verified_condition_ids=("condition.ready",),
        ),
    }
    values.update(overrides)
    return ScenarioDefinition.model_validate(values)
