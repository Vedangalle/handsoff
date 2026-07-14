"""Evidence-first comparison of deterministic and contextual demonstration runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.domain.goals import AcceptanceCondition
    from handsoff.domain.plans import PlannedAction, PlanProposal
    from handsoff.presentation.facade import DemoRun


class ProposalChange(StrEnum):
    """Semantic relationship between one baseline and contextual action."""

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class ActionSemantics:
    """Plan-action meaning after generated identity fields are removed."""

    capability_id: str
    occurrence: int
    capability_version: str
    target_entity_id: str
    parameters: str
    dependency_capabilities: tuple[str, ...]
    failure_strategy: str
    preconditions: tuple[str, ...]
    acceptance_conditions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProposalDelta:
    """One reviewable semantic action difference between two proposals."""

    capability_id: str
    occurrence: int
    change: ProposalChange
    changed_fields: tuple[str, ...]
    baseline: ActionSemantics | None
    contextual: ActionSemantics | None


@dataclass(frozen=True, slots=True)
class DemoComparison:
    """Two complete executions plus explicit cross-run invariants."""

    baseline: DemoRun
    contextual: DemoRun
    proposal_deltas: tuple[ProposalDelta, ...]
    trusted_inputs_match: bool
    contextual_capabilities_declared: bool
    policy_decision_match: bool
    terminal_states_match: bool
    verification_results_match: bool

    @property
    def changed_deltas(self) -> tuple[ProposalDelta, ...]:
        """Return only action semantics that differ from the baseline."""
        return tuple(
            delta for delta in self.proposal_deltas if delta.change is not ProposalChange.UNCHANGED
        )

    @property
    def live_provider_path(self) -> bool:
        """Report whether both optional providers completed without fallback."""
        planner = self.contextual.assessment.runtime.planner
        return (
            planner.provider == "google"
            and not planner.used_fallback
            and self.contextual.memory.provider == "supermemory"
            and not self.contextual.memory.used_fallback
        )


def compare_runs(baseline: DemoRun, contextual: DemoRun) -> DemoComparison:
    """Compare two executions without treating generated identities as behavior."""
    baseline_plan = baseline.assessment.runtime.planner.plan
    contextual_plan = contextual.assessment.runtime.planner.plan
    declared = {capability.capability_id for capability in contextual.scenario.capabilities}
    proposed = {action.capability_id for action in contextual_plan.actions}
    return DemoComparison(
        baseline=baseline,
        contextual=contextual,
        proposal_deltas=_compare_plans(baseline_plan, contextual_plan),
        trusted_inputs_match=(
            baseline.trusted_input_fingerprint == contextual.trusted_input_fingerprint
        ),
        contextual_capabilities_declared=proposed <= declared,
        policy_decision_match=(
            baseline.assessment.runtime.policy.decision
            is contextual.assessment.runtime.policy.decision
        ),
        terminal_states_match=(
            baseline.assessment.runtime.terminal_plan_state
            is contextual.assessment.runtime.terminal_plan_state
        ),
        verification_results_match=(
            baseline.assessment.runtime.verifications == contextual.assessment.runtime.verifications
        ),
    )


def _compare_plans(
    baseline: PlanProposal,
    contextual: PlanProposal,
) -> tuple[ProposalDelta, ...]:
    """Pair actions by declared capability and stable occurrence."""
    baseline_actions = {
        (action.capability_id, action.occurrence): action for action in _action_semantics(baseline)
    }
    contextual_actions = {
        (action.capability_id, action.occurrence): action
        for action in _action_semantics(contextual)
    }
    deltas: list[ProposalDelta] = []
    for capability_id, occurrence in sorted(baseline_actions.keys() | contextual_actions.keys()):
        baseline_action = baseline_actions.get((capability_id, occurrence))
        contextual_action = contextual_actions.get((capability_id, occurrence))
        changed_fields: tuple[str, ...]
        if baseline_action is None:
            change = ProposalChange.ADDED
            changed_fields = ("action",)
        elif contextual_action is None:
            change = ProposalChange.REMOVED
            changed_fields = ("action",)
        else:
            changed_fields = _changed_fields(baseline_action, contextual_action)
            change = ProposalChange.MODIFIED if changed_fields else ProposalChange.UNCHANGED
        deltas.append(
            ProposalDelta(
                capability_id=capability_id,
                occurrence=occurrence,
                change=change,
                changed_fields=changed_fields,
                baseline=baseline_action,
                contextual=contextual_action,
            )
        )
    return tuple(deltas)


def _action_semantics(plan: PlanProposal) -> tuple[ActionSemantics, ...]:
    """Normalize action references while retaining policy-relevant meaning."""
    action_capabilities = {action.action_id: action.capability_id for action in plan.actions}
    occurrences: dict[str, int] = {}
    normalized: list[ActionSemantics] = []
    for action in sorted(plan.actions, key=lambda item: (item.capability_id, item.action_id)):
        occurrence = occurrences.get(action.capability_id, 0) + 1
        occurrences[action.capability_id] = occurrence
        normalized.append(_normalize_action(action, occurrence, action_capabilities))
    return tuple(normalized)


def _normalize_action(
    action: PlannedAction,
    occurrence: int,
    action_capabilities: dict[str, str],
) -> ActionSemantics:
    """Strip generated identifiers and canonicalize nested typed values."""
    return ActionSemantics(
        capability_id=action.capability_id,
        occurrence=occurrence,
        capability_version=action.capability_version,
        target_entity_id=action.target_entity_id,
        parameters=json.dumps(action.parameters, sort_keys=True, separators=(",", ":")),
        dependency_capabilities=tuple(
            sorted(action_capabilities[dependency] for dependency in action.depends_on)
        ),
        failure_strategy=action.on_failure.value,
        preconditions=_canonical_conditions(action.preconditions),
        acceptance_conditions=_canonical_conditions(action.acceptance_conditions),
    )


def _canonical_conditions(conditions: tuple[AcceptanceCondition, ...]) -> tuple[str, ...]:
    """Return stable JSON for Pydantic condition contracts."""
    return tuple(
        sorted(
            json.dumps(condition.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
            for condition in conditions
        )
    )


def _changed_fields(
    baseline: ActionSemantics,
    contextual: ActionSemantics,
) -> tuple[str, ...]:
    """Name every policy- or evidence-relevant field that changed."""
    field_names = (
        "capability_version",
        "target_entity_id",
        "parameters",
        "dependency_capabilities",
        "failure_strategy",
        "preconditions",
        "acceptance_conditions",
    )
    return tuple(
        field_name
        for field_name in field_names
        if getattr(baseline, field_name) != getattr(contextual, field_name)
    )


__all__ = [
    "ActionSemantics",
    "DemoComparison",
    "ProposalChange",
    "ProposalDelta",
    "compare_runs",
]
