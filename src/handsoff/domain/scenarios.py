"""Deterministic simulation-scenario contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from handsoff.domain import ContractModel, ContractVersion, Identifier, NonEmptyText, UtcDateTime
from handsoff.domain.capabilities import AutonomyMode, CapabilityContract, RiskClass
from handsoff.domain.execution import PlanState
from handsoff.domain.goals import Goal  # noqa: TC001
from handsoff.domain.observations import Observation  # noqa: TC001
from handsoff.domain.policies import PolicyDecision


class ScriptedResult(StrEnum):
    """A deterministic adapter outcome supplied by a scenario fixture."""

    ADAPTER_ACCEPTED = "adapter_accepted"
    EFFECT_OBSERVED = "effect_observed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ScriptedCapabilityOutcome(ContractModel):
    """Scripted result for one capability attempt in a future simulator."""

    capability_id: Identifier
    attempt: Annotated[int, Field(ge=1)]
    result: ScriptedResult
    effect_observations: tuple[Observation, ...] = ()

    @model_validator(mode="after")
    def validate_effect_evidence(self) -> Self:
        """Require observed-effect outcomes to include observations."""
        if self.result is ScriptedResult.EFFECT_OBSERVED and not self.effect_observations:
            message = "effect_observed requires at least one effect observation"
            raise ValueError(message)
        if self.result is not ScriptedResult.EFFECT_OBSERVED and self.effect_observations:
            message = "only effect_observed outcomes may contain effect observations"
            raise ValueError(message)
        return self


class ScenarioExpectation(ContractModel):
    """Expected deterministic result used by future scenario tests."""

    policy_decision: PolicyDecision
    terminal_plan_state: PlanState
    dispatched_capability_ids: tuple[Identifier, ...] = ()
    withheld_capability_ids: tuple[Identifier, ...] = ()
    verified_condition_ids: tuple[Identifier, ...] = ()
    unsatisfied_condition_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def validate_disjoint_expectations(self) -> Self:
        """Prevent one capability or condition from having contradictory outcomes."""
        if set(self.dispatched_capability_ids) & set(self.withheld_capability_ids):
            message = "a capability cannot be both dispatched and withheld"
            raise ValueError(message)
        if set(self.verified_condition_ids) & set(self.unsatisfied_condition_ids):
            message = "a condition cannot be both verified and unsatisfied"
            raise ValueError(message)
        for values, label in (
            (self.dispatched_capability_ids, "dispatched capability"),
            (self.withheld_capability_ids, "withheld capability"),
            (self.verified_condition_ids, "verified condition"),
            (self.unsatisfied_condition_ids, "unsatisfied condition"),
        ):
            if len(values) != len(set(values)):
                message = f"{label} identifiers must be unique"
                raise ValueError(message)
        return self


class ScenarioDefinition(ContractModel):
    """Self-contained, deterministic input fixture for the future simulator."""

    schema_version: ContractVersion
    scenario_id: Identifier
    title: NonEmptyText
    description: NonEmptyText
    simulation_only: Literal[True]
    clock_start_at: UtcDateTime
    goal: Goal
    capabilities: Annotated[tuple[CapabilityContract, ...], Field(min_length=1)]
    initial_observations: Annotated[tuple[Observation, ...], Field(min_length=1)]
    scripted_outcomes: tuple[ScriptedCapabilityOutcome, ...] = ()
    expected: ScenarioExpectation

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        """Cross-check all fixture references and simulation-only boundaries."""
        self._validate_unique_entities()
        self._validate_references()
        self._validate_timeline()
        self._validate_capability_boundaries()
        self._validate_expected_terminal_state()
        return self

    def _validate_unique_entities(self) -> None:
        """Require unique capabilities, observations, and scripted attempts."""
        capability_ids = [capability.capability_id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            message = "scenario capability identifiers must be unique"
            raise ValueError(message)

        observation_ids = [observation.observation_id for observation in self.initial_observations]
        if len(observation_ids) != len(set(observation_ids)):
            message = "initial observation identifiers must be unique"
            raise ValueError(message)

        outcome_keys = [
            (outcome.capability_id, outcome.attempt) for outcome in self.scripted_outcomes
        ]
        if len(outcome_keys) != len(set(outcome_keys)):
            message = "scripted capability attempts must be unique"
            raise ValueError(message)

    def _validate_references(self) -> None:
        """Require all expectation and script references to be declared."""
        declared_capabilities = {capability.capability_id for capability in self.capabilities}
        referenced_capabilities = (
            {outcome.capability_id for outcome in self.scripted_outcomes}
            | set(self.expected.dispatched_capability_ids)
            | set(self.expected.withheld_capability_ids)
        )
        if not referenced_capabilities <= declared_capabilities:
            message = "scenario references an undeclared capability"
            raise ValueError(message)

        condition_ids = {condition.condition_id for condition in self.goal.acceptance_conditions}
        referenced_conditions = set(self.expected.verified_condition_ids) | set(
            self.expected.unsatisfied_condition_ids
        )
        if not referenced_conditions <= condition_ids:
            message = "scenario expectation references an undeclared goal condition"
            raise ValueError(message)

    def _validate_timeline(self) -> None:
        """Require deterministic request and observation time ordering."""
        if self.goal.requested_at != self.clock_start_at:
            message = "scenario goal request time must equal the deterministic clock start"
            raise ValueError(message)

        if any(
            observation.observed_at > self.clock_start_at
            for observation in self.initial_observations
        ):
            message = "initial observations cannot occur after the scenario clock start"
            raise ValueError(message)

        if any(
            observation.observed_at < self.clock_start_at
            for outcome in self.scripted_outcomes
            for observation in outcome.effect_observations
        ):
            message = "effect observations cannot occur before the scenario clock start"
            raise ValueError(message)

    def _validate_capability_boundaries(self) -> None:
        """Keep reference fixtures free of R3 and non-simulation capability modes."""
        for capability in self.capabilities:
            if capability.risk_class is RiskClass.R3:
                message = "reference scenarios cannot declare R3 capabilities"
                raise ValueError(message)
            if not capability.supported_modes <= {AutonomyMode.SIMULATION}:
                message = "reference scenario capabilities must be simulation-only"
                raise ValueError(message)

    def _validate_expected_terminal_state(self) -> None:
        """Require the expected terminal state to agree with policy."""
        terminal_by_policy = {
            PolicyDecision.DENY: {PlanState.REJECTED},
            PolicyDecision.REQUIRE_APPROVAL: {PlanState.AWAITING_APPROVAL},
            PolicyDecision.ALLOW: {
                PlanState.SUCCEEDED,
                PlanState.PARTIALLY_SUCCEEDED,
                PlanState.FAILED,
                PlanState.COMPENSATED,
            },
        }
        if (
            self.expected.terminal_plan_state
            not in terminal_by_policy[self.expected.policy_decision]
        ):
            message = "terminal plan state is inconsistent with the expected policy decision"
            raise ValueError(message)


__all__ = [
    "ScenarioDefinition",
    "ScenarioExpectation",
    "ScriptedCapabilityOutcome",
    "ScriptedResult",
]
