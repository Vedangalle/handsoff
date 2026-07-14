"""Full deterministic runtime lifecycle tests."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from handsoff.adapters.devices.simulator import ScriptedSimulatorAdapter
from handsoff.adapters.persistence.memory import InMemoryLedger
from handsoff.adapters.planner import DeterministicPlanner
from handsoff.application.capability_registry import CapabilityRegistry
from handsoff.application.execute_plan import PlanExecutor, RuntimeResult
from handsoff.application.world_model import WorldModel
from handsoff.domain.capabilities import AuthorizationRequirement, AutonomyMode, CapabilityContract
from handsoff.domain.execution import ActionState, PlanState, PlanTransition
from handsoff.domain.plans import FailureStrategy
from handsoff.domain.policies import Approval, PolicyDecision
from handsoff.domain.scenarios import ScriptedCapabilityOutcome, ScriptedResult
from handsoff.ports.planner import PlannerRequest, PlannerResult
from tests.fixtures.contracts import (
    NOW,
    make_action,
    make_capability,
    make_goal,
    make_observation,
    make_plan,
)

if TYPE_CHECKING:
    from handsoff.domain.observations import Observation

EXECUTION_RESOLVE_CALL = 3
DISPATCH_RESOLVE_CALL = 4


def planner_result(
    capabilities: tuple[CapabilityContract, ...] | None = None,
) -> PlannerResult:
    """Produce the offline plan for a test registry."""
    typed = capabilities or (make_capability(),)
    request = PlannerRequest(
        goal=make_goal(),
        observations=(make_observation(),),
        capabilities=typed,
        mode=AutonomyMode.SIMULATION,
        now=NOW,
    )
    return DeterministicPlanner().propose(request)


def run_single(
    outcome: ScriptedResult,
    *,
    capability: CapabilityContract | None = None,
    approval: Approval | None = None,
    observations: tuple[Observation, ...] | None = None,
) -> RuntimeResult:
    """Run a one-action lifecycle with a selected adapter outcome."""
    typed_capability = capability or make_capability()
    initial = observations or (make_observation(),)
    effects: tuple[Observation, ...] = ()
    if outcome is ScriptedResult.EFFECT_OBSERVED:
        effects = (
            make_observation(
                observation_id="observation.effect",
                value="ready",
                observed_at=NOW + timedelta(seconds=1),
            ),
        )
    scripted = ScriptedCapabilityOutcome(
        capability_id="device.prepare",
        attempt=1,
        result=outcome,
        effect_observations=effects,
    )
    plan_result = planner_result((typed_capability,))
    return PlanExecutor(
        CapabilityRegistry((typed_capability,)),
        WorldModel(initial),
        ScriptedSimulatorAdapter((scripted,)),
        InMemoryLedger(),
    ).run(make_goal(), plan_result, NOW, approval)


def test_runtime_distinguishes_dispatch_observation_and_verification() -> None:
    """The successful lifecycle preserves every evidence boundary."""
    result = run_single(ScriptedResult.EFFECT_OBSERVED)
    assert result.policy.decision is PolicyDecision.ALLOW
    assert result.terminal_plan_state is PlanState.SUCCEEDED
    states = [transition.to_state for transition in result.action_transitions]
    assert states == [
        ActionState.AUTHORIZED,
        ActionState.DISPATCHED,
        ActionState.ADAPTER_ACCEPTED,
        ActionState.EFFECT_OBSERVED,
        ActionState.VERIFIED,
    ]
    assert result.dispatched_capability_ids == ("device.prepare",)
    payload = result.events[-1].payload
    assert isinstance(payload, PlanTransition)
    assert payload.to_state is PlanState.SUCCEEDED


def test_adapter_acceptance_without_effect_evidence_fails() -> None:
    """SDK acceptance alone cannot produce success."""
    result = run_single(ScriptedResult.ADAPTER_ACCEPTED)
    assert result.terminal_plan_state is PlanState.FAILED
    assert result.action_transitions[-1].to_state is ActionState.FAILED


def test_timeout_records_failure_and_failed_terminal_state() -> None:
    """Timeout is explicit in both action state and evidence ledger."""
    result = run_single(ScriptedResult.TIMED_OUT)
    assert result.terminal_plan_state is PlanState.FAILED
    assert any(
        transition.to_state is ActionState.TIMED_OUT for transition in result.action_transitions
    )
    assert any(event.kind.value == "failure_recorded" for event in result.events)


def test_failed_dispatch_produces_no_false_success() -> None:
    """A failed action with no verified condition terminates failed."""
    result = run_single(ScriptedResult.FAILED)
    assert result.terminal_plan_state is PlanState.FAILED


def test_required_approval_stops_before_dispatch() -> None:
    """No approval means awaiting approval and zero adapter calls."""
    capability = make_capability(authorization=AuthorizationRequirement.APPROVAL)
    result = run_single(ScriptedResult.EFFECT_OBSERVED, capability=capability)
    assert result.terminal_plan_state is PlanState.AWAITING_APPROVAL
    assert result.dispatched_capability_ids == ()
    assert result.withheld_capability_ids == ("device.prepare",)


def make_approval(**overrides: object) -> Approval:
    """Build approval for the deterministic single-action plan."""
    values: dict[str, object] = {
        "approval_id": "approval.arrival",
        "plan_id": "plan.arrival",
        "policy_evaluation_id": "policy-evaluation.arrival",
        "approver_id": "operator.demo",
        "approved_action_ids": ("action.device-prepare",),
        "issued_at": NOW,
        "expires_at": NOW + timedelta(minutes=1),
    }
    values.update(overrides)
    return Approval.model_validate(values)


def test_valid_approval_authorizes_exact_scope() -> None:
    """A current exact approval crosses the explicit human boundary."""
    capability = make_capability(authorization=AuthorizationRequirement.APPROVAL)
    result = run_single(
        ScriptedResult.EFFECT_OBSERVED,
        capability=capability,
        approval=make_approval(),
    )
    assert result.terminal_plan_state is PlanState.SUCCEEDED
    assert any(event.kind.value == "approval_recorded" for event in result.events)
    assert result.withheld_capability_ids == ()


def test_expired_approval_cannot_authorize() -> None:
    """Approval expiration fails closed before execution."""
    capability = make_capability(authorization=AuthorizationRequirement.APPROVAL)
    approval = make_approval(
        issued_at=NOW - timedelta(minutes=2),
        expires_at=NOW,
    )
    result = run_single(ScriptedResult.EFFECT_OBSERVED, capability=capability, approval=approval)
    assert result.terminal_plan_state is PlanState.EXPIRED


def test_wrong_approval_scope_is_rejected() -> None:
    """Approval is bound to the exact policy evaluation and action set."""
    capability = make_capability(authorization=AuthorizationRequirement.APPROVAL)
    approval = make_approval(policy_evaluation_id="policy-evaluation.other")
    result = run_single(ScriptedResult.EFFECT_OBSERVED, capability=capability, approval=approval)
    assert result.terminal_plan_state is PlanState.REJECTED


def test_bounded_retry_can_recover_on_second_attempt() -> None:
    """Failures retry at most the declared number of attempts."""
    capability = make_capability(max_attempts=2)
    outcomes = (
        ScriptedCapabilityOutcome(
            capability_id="device.prepare",
            attempt=1,
            result=ScriptedResult.FAILED,
        ),
        ScriptedCapabilityOutcome(
            capability_id="device.prepare",
            attempt=2,
            result=ScriptedResult.EFFECT_OBSERVED,
            effect_observations=(
                make_observation(
                    observation_id="observation.effect",
                    value="ready",
                    observed_at=NOW + timedelta(seconds=1),
                ),
            ),
        ),
    )
    result = PlanExecutor(
        CapabilityRegistry((capability,)),
        WorldModel((make_observation(),)),
        ScriptedSimulatorAdapter(outcomes),
        InMemoryLedger(),
    ).run(make_goal(), planner_result((capability,)), NOW)
    assert result.terminal_plan_state is PlanState.SUCCEEDED


def test_bounded_retry_stops_after_first_success() -> None:
    """A successful first attempt never consumes the remaining retry budget."""
    capability = make_capability(max_attempts=2)
    outcome = ScriptedCapabilityOutcome(
        capability_id="device.prepare",
        attempt=1,
        result=ScriptedResult.EFFECT_OBSERVED,
        effect_observations=(
            make_observation(
                observation_id="observation.effect",
                value="ready",
                observed_at=NOW + timedelta(seconds=1),
            ),
        ),
    )
    result = PlanExecutor(
        CapabilityRegistry((capability,)),
        WorldModel((make_observation(),)),
        ScriptedSimulatorAdapter((outcome,)),
        InMemoryLedger(),
    ).run(make_goal(), planner_result((capability,)), NOW)
    assert result.terminal_plan_state is PlanState.SUCCEEDED


def test_executor_detects_registry_loss_after_policy() -> None:
    """A capability disappearing between policy and execution aborts safely."""
    capability = make_capability()
    registry = CapabilityRegistry((capability,))
    original_resolve = registry.resolve
    calls = 0

    def resolve(capability_id: str, version: str) -> CapabilityContract | None:
        nonlocal calls
        calls += 1
        if calls >= EXECUTION_RESOLVE_CALL:
            return None
        return original_resolve(capability_id, version)

    registry.resolve = MagicMock(side_effect=resolve)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="unavailable capability"):
        PlanExecutor(
            registry,
            WorldModel((make_observation(),)),
            ScriptedSimulatorAdapter(()),
            InMemoryLedger(),
        ).run(make_goal(), planner_result(), NOW)


def test_executor_detects_registry_change_before_dispatch() -> None:
    """A changed contract identity cannot cross the adapter boundary."""
    capability = make_capability()
    registry = CapabilityRegistry((capability,))
    original_resolve = registry.resolve
    calls = 0

    def resolve(capability_id: str, version: str) -> CapabilityContract | None:
        nonlocal calls
        calls += 1
        if calls >= DISPATCH_RESOLVE_CALL:
            return make_capability(description="Changed declaration")
        return original_resolve(capability_id, version)

    registry.resolve = MagicMock(side_effect=resolve)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="changed during execution"):
        PlanExecutor(
            registry,
            WorldModel((make_observation(),)),
            ScriptedSimulatorAdapter(()),
            InMemoryLedger(),
        ).run(make_goal(), planner_result(), NOW)


def test_failed_dependency_is_never_dispatched() -> None:
    """A dependent action fails before its adapter boundary."""
    first_capability = make_capability()
    second_capability = make_capability(
        capability_id="device.second",
        target_entity_id="device.primary",
    )
    first = make_action(on_failure=FailureStrategy.CONTINUE)
    second = make_action(
        action_id="action.second",
        capability_id="device.second",
        depends_on=("action.prepare",),
        idempotency_key="idempotency.second",
    )
    plan = make_plan(actions=(first, second))
    result = PlanExecutor(
        CapabilityRegistry((first_capability, second_capability)),
        WorldModel((make_observation(),)),
        ScriptedSimulatorAdapter(
            (
                ScriptedCapabilityOutcome(
                    capability_id="device.prepare",
                    attempt=1,
                    result=ScriptedResult.FAILED,
                ),
            )
        ),
        InMemoryLedger(),
    ).run(
        make_goal(),
        PlannerResult(
            plan=plan,
            provider="test",
            model="test",
            used_fallback=False,
            latency_ms=0.0,
        ),
        NOW,
    )
    assert result.dispatched_capability_ids == ("device.prepare",)
    assert result.action_transitions[-1].to_state is ActionState.FAILED
