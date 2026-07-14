"""Single-owner deterministic plan execution and verification lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from handsoff.application.conditions import ConditionEvaluator
from handsoff.application.evaluate_plan import PolicyKernel
from handsoff.application.ledger import LedgerRecorder
from handsoff.application.verify_outcome import OutcomeVerifier
from handsoff.domain.events import EventKind, FailureRecord, LedgerEvent
from handsoff.domain.execution import (
    ActionState,
    ActionTransition,
    PlanState,
    PlanTransition,
    VerificationResult,
)
from handsoff.domain.policies import Approval, PolicyDecision, PolicyEvaluation
from handsoff.ports.capability_adapter import CapabilityAdapter, DispatchResult, DispatchStatus

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.application.capability_registry import CapabilityRegistry
    from handsoff.application.world_model import WorldModel
    from handsoff.domain.capabilities import CapabilityContract
    from handsoff.domain.goals import Goal
    from handsoff.domain.plans import PlannedAction, PlanProposal
    from handsoff.ports.planner import PlannerResult
    from handsoff.ports.repositories import LedgerRepository


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    """Complete deterministic outcome and evidence surface."""

    planner: PlannerResult
    policy: PolicyEvaluation
    terminal_plan_state: PlanState
    plan_transitions: tuple[PlanTransition, ...]
    action_transitions: tuple[ActionTransition, ...]
    verifications: tuple[VerificationResult, ...]
    dispatched_capability_ids: tuple[str, ...]
    withheld_capability_ids: tuple[str, ...]
    events: tuple[LedgerEvent, ...]


class PlanExecutor:
    """Own the prototype execution state machine in one process."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        world: WorldModel,
        adapter: CapabilityAdapter,
        ledger: LedgerRepository,
    ) -> None:
        """Bind one registry, world, adapter, and evidence ledger."""
        self._registry = registry
        self._world = world
        self._adapter = adapter
        self._ledger = ledger
        self._conditions = ConditionEvaluator()

    def run(
        self,
        goal: Goal,
        planner: PlannerResult,
        now: datetime,
        approval: Approval | None = None,
    ) -> RuntimeResult:
        """Policy-check, optionally authorize, execute, and independently verify."""
        plan = planner.plan
        recorder = LedgerRecorder(self._ledger, plan.plan_id)
        plan_transitions: list[PlanTransition] = []
        action_transitions: list[ActionTransition] = []

        recorder.record(EventKind.GOAL_RECEIVED, goal, now)
        for observation in self._world.observations():
            recorder.record(EventKind.OBSERVATION_RECORDED, observation, observation.observed_at)
        recorder.record(EventKind.PLAN_PROPOSED, plan, plan.created_at)
        self._plan_transition(
            plan,
            PlanState.PROPOSED,
            PlanState.VALIDATED,
            now,
            "Plan contract validated",
            plan_transitions,
            recorder,
        )

        policy = PolicyKernel(self._registry, self._world).evaluate(plan, now)
        recorder.record(EventKind.POLICY_EVALUATED, policy, now)
        self._plan_transition(
            plan,
            PlanState.VALIDATED,
            PlanState.POLICY_EVALUATED,
            now,
            "Deterministic policy evaluated",
            plan_transitions,
            recorder,
        )

        denied = tuple(
            action.capability_id
            for action, decision in zip(plan.actions, policy.action_decisions, strict=True)
            if decision.decision is PolicyDecision.DENY
        )
        pending_approval = tuple(
            action.capability_id
            for action, decision in zip(plan.actions, policy.action_decisions, strict=True)
            if decision.decision is PolicyDecision.REQUIRE_APPROVAL
        )
        if policy.decision is PolicyDecision.DENY:
            self._plan_transition(
                plan,
                PlanState.POLICY_EVALUATED,
                PlanState.REJECTED,
                now,
                "Policy denied at least one action",
                plan_transitions,
                recorder,
            )
            return self._finish_without_execution(
                goal, planner, policy, PlanState.REJECTED, plan_transitions, denied, now, recorder
            )

        current_state = PlanState.POLICY_EVALUATED
        if policy.decision is PolicyDecision.REQUIRE_APPROVAL:
            self._plan_transition(
                plan,
                current_state,
                PlanState.AWAITING_APPROVAL,
                now,
                "Explicit approval is required",
                plan_transitions,
                recorder,
            )
            current_state = PlanState.AWAITING_APPROVAL
            approval_state = self._approval_state(plan, policy, approval, now)
            if approval_state is None:
                return self._finish_without_execution(
                    goal,
                    planner,
                    policy,
                    PlanState.AWAITING_APPROVAL,
                    plan_transitions,
                    (*denied, *pending_approval),
                    now,
                    recorder,
                )
            if approval_state is not PlanState.APPROVED:
                self._plan_transition(
                    plan,
                    current_state,
                    approval_state,
                    now,
                    "Approval is invalid or expired",
                    plan_transitions,
                    recorder,
                )
                return self._finish_without_execution(
                    goal,
                    planner,
                    policy,
                    approval_state,
                    plan_transitions,
                    (*denied, *pending_approval),
                    now,
                    recorder,
                )
            recorder.record(EventKind.APPROVAL_RECORDED, cast("Approval", approval), now)

        self._plan_transition(
            plan,
            current_state,
            PlanState.APPROVED,
            now,
            "Policy and approval boundary satisfied",
            plan_transitions,
            recorder,
        )
        self._plan_transition(
            plan,
            PlanState.APPROVED,
            PlanState.EXECUTING,
            now,
            "Execution started",
            plan_transitions,
            recorder,
        )

        action_states: dict[str, ActionState] = {}
        dispatched: list[str] = []
        effective_now = now
        for action in plan.actions:
            effective_now = self._execute_action(
                action,
                action_states,
                dispatched,
                effective_now,
                action_transitions,
                recorder,
            )

        self._plan_transition(
            plan,
            PlanState.EXECUTING,
            PlanState.VERIFYING,
            effective_now,
            "All bounded dispatch attempts completed",
            plan_transitions,
            recorder,
        )
        verifications = OutcomeVerifier(self._world).verify(goal, effective_now)
        for verification in verifications:
            recorder.record(EventKind.VERIFICATION_RECORDED, verification, effective_now)
        self._finalize_actions(
            plan,
            action_states,
            effective_now,
            action_transitions,
            recorder,
        )
        terminal = self._terminal_state(verifications, action_states)
        self._plan_transition(
            plan,
            PlanState.VERIFYING,
            terminal,
            effective_now,
            "Terminal state derived from action and goal verification evidence",
            plan_transitions,
            recorder,
        )
        return RuntimeResult(
            planner=planner,
            policy=policy,
            terminal_plan_state=terminal,
            plan_transitions=tuple(plan_transitions),
            action_transitions=tuple(action_transitions),
            verifications=verifications,
            dispatched_capability_ids=tuple(dispatched),
            withheld_capability_ids=denied,
            events=self._ledger.list_stream(plan.plan_id),
        )

    def _execute_action(  # noqa: PLR0913 - lifecycle collections are explicit state outputs
        self,
        action: PlannedAction,
        action_states: dict[str, ActionState],
        dispatched: list[str],
        now: datetime,
        transitions: list[ActionTransition],
        recorder: LedgerRecorder,
    ) -> datetime:
        capability = self._registry.resolve(action.capability_id, action.capability_version)
        if capability is None:
            message = "authorized plan references an unavailable capability"
            raise RuntimeError(message)
        self._action_transition(
            action,
            ActionState.PROPOSED,
            ActionState.AUTHORIZED,
            now,
            "Action covered by the plan policy decision",
            transitions,
            recorder,
        )
        if any(
            action_states.get(dependency) is not ActionState.VERIFIED
            for dependency in action.depends_on
        ):
            self._action_transition(
                action,
                ActionState.AUTHORIZED,
                ActionState.FAILED,
                now,
                "A required dependency did not verify",
                transitions,
                recorder,
            )
            action_states[action.action_id] = ActionState.FAILED
            return now

        self._action_transition(
            action,
            ActionState.AUTHORIZED,
            ActionState.DISPATCHED,
            now,
            "Bounded simulator dispatch started",
            transitions,
            recorder,
        )
        dispatched.append(action.capability_id)
        result = self._dispatch_with_retries(action, capability)
        state = self._record_dispatch_result(action, result, now, transitions, recorder)
        action_states[action.action_id] = state
        effective_now = now
        for observation in result.observations:
            self._world.record(observation)
            recorder.record(EventKind.OBSERVATION_RECORDED, observation, observation.observed_at)
            effective_now = max(effective_now, observation.observed_at)
        if state in {ActionState.FAILED, ActionState.TIMED_OUT}:
            recorder.record(
                EventKind.FAILURE_RECORDED,
                FailureRecord(
                    failure_code=f"dispatch.{state.value}",
                    summary=result.reason,
                    retryable=False,
                    subject_id=action.action_id,
                ),
                effective_now,
            )
        return effective_now

    def _dispatch_with_retries(
        self,
        action: PlannedAction,
        capability: CapabilityContract,
    ) -> DispatchResult:
        if (
            self._registry.resolve(action.capability_id, action.capability_version)
            is not capability
        ):
            message = "capability registry changed during execution"
            raise RuntimeError(message)
        result = self._adapter.dispatch(action, capability, 1)
        for attempt in range(2, capability.max_attempts + 1):
            if result.status in {DispatchStatus.ADAPTER_ACCEPTED, DispatchStatus.EFFECT_OBSERVED}:
                break
            result = self._adapter.dispatch(action, capability, attempt)
        return result

    def _record_dispatch_result(
        self,
        action: PlannedAction,
        result: DispatchResult,
        now: datetime,
        transitions: list[ActionTransition],
        recorder: LedgerRecorder,
    ) -> ActionState:
        if result.status is DispatchStatus.FAILED:
            target = ActionState.FAILED
        elif result.status is DispatchStatus.TIMED_OUT:
            target = ActionState.TIMED_OUT
        else:
            target = ActionState.ADAPTER_ACCEPTED
        self._action_transition(
            action,
            ActionState.DISPATCHED,
            target,
            now,
            result.reason,
            transitions,
            recorder,
        )
        if result.status is DispatchStatus.EFFECT_OBSERVED:
            self._action_transition(
                action,
                ActionState.ADAPTER_ACCEPTED,
                ActionState.EFFECT_OBSERVED,
                now,
                "Independent simulated telemetry observed",
                transitions,
                recorder,
            )
            return ActionState.EFFECT_OBSERVED
        if result.status is DispatchStatus.ADAPTER_ACCEPTED:
            self._action_transition(
                action,
                ActionState.ADAPTER_ACCEPTED,
                ActionState.FAILED,
                now,
                "Adapter acceptance supplied no effect evidence",
                transitions,
                recorder,
            )
            return ActionState.FAILED
        return target

    def _finalize_actions(
        self,
        plan: PlanProposal,
        states: dict[str, ActionState],
        now: datetime,
        transitions: list[ActionTransition],
        recorder: LedgerRecorder,
    ) -> None:
        for action in plan.actions:
            if states.get(action.action_id) is not ActionState.EFFECT_OBSERVED:
                continue
            checks = [
                self._conditions.evaluate(condition, self._world, now)
                for condition in action.acceptance_conditions
            ]
            target = (
                ActionState.VERIFIED
                if all(check.satisfied for check in checks)
                else ActionState.FAILED
            )
            reason = (
                "Action acceptance conditions verified"
                if target is ActionState.VERIFIED
                else "Action effect did not satisfy acceptance conditions"
            )
            self._action_transition(
                action,
                ActionState.EFFECT_OBSERVED,
                target,
                now,
                reason,
                transitions,
                recorder,
            )
            states[action.action_id] = target

    @staticmethod
    def _terminal_state(
        verifications: tuple[VerificationResult, ...],
        action_states: dict[str, ActionState],
    ) -> PlanState:
        all_verified = all(result.satisfied for result in verifications)
        all_actions_verified = all(
            state is ActionState.VERIFIED for state in action_states.values()
        )
        if all_verified and all_actions_verified:
            return PlanState.SUCCEEDED
        if any(result.satisfied for result in verifications) or any(
            state is ActionState.VERIFIED for state in action_states.values()
        ):
            return PlanState.PARTIALLY_SUCCEEDED
        return PlanState.FAILED

    @staticmethod
    def _approval_state(
        plan: PlanProposal,
        policy: PolicyEvaluation,
        approval: Approval | None,
        now: datetime,
    ) -> PlanState | None:
        if approval is None:
            return None
        if approval.expires_at <= now:
            return PlanState.EXPIRED
        required = {
            decision.action_id
            for decision in policy.action_decisions
            if decision.decision is PolicyDecision.REQUIRE_APPROVAL
        }
        if (
            approval.plan_id != plan.plan_id
            or approval.policy_evaluation_id != policy.evaluation_id
            or set(approval.approved_action_ids) != required
        ):
            return PlanState.REJECTED
        return PlanState.APPROVED

    def _finish_without_execution(  # noqa: PLR0913 - explicit evidence inputs avoid hidden state
        self,
        goal: Goal,
        planner: PlannerResult,
        policy: PolicyEvaluation,
        terminal: PlanState,
        transitions: list[PlanTransition],
        withheld: tuple[str, ...],
        now: datetime,
        recorder: LedgerRecorder,
    ) -> RuntimeResult:
        verifications = OutcomeVerifier(self._world).verify(goal, now)
        for verification in verifications:
            recorder.record(EventKind.VERIFICATION_RECORDED, verification, now)
        return RuntimeResult(
            planner=planner,
            policy=policy,
            terminal_plan_state=terminal,
            plan_transitions=tuple(transitions),
            action_transitions=(),
            verifications=verifications,
            dispatched_capability_ids=(),
            withheld_capability_ids=withheld,
            events=self._ledger.list_stream(planner.plan.plan_id),
        )

    @staticmethod
    def _plan_transition(  # noqa: PLR0913 - transition construction remains explicit
        plan: PlanProposal,
        source: PlanState,
        target: PlanState,
        now: datetime,
        reason: str,
        transitions: list[PlanTransition],
        recorder: LedgerRecorder,
    ) -> None:
        transition = PlanTransition(
            plan_id=plan.plan_id,
            from_state=source,
            to_state=target,
            occurred_at=now,
            reason=reason,
        )
        transitions.append(transition)
        recorder.record(EventKind.PLAN_TRANSITIONED, transition, now)

    @staticmethod
    def _action_transition(  # noqa: PLR0913 - transition construction remains explicit
        action: PlannedAction,
        source: ActionState,
        target: ActionState,
        now: datetime,
        reason: str,
        transitions: list[ActionTransition],
        recorder: LedgerRecorder,
    ) -> None:
        transition = ActionTransition(
            action_id=action.action_id,
            from_state=source,
            to_state=target,
            occurred_at=now,
            reason=reason,
        )
        transitions.append(transition)
        recorder.record(EventKind.ACTION_TRANSITIONED, transition, now)


__all__ = ["PlanExecutor", "RuntimeResult"]
