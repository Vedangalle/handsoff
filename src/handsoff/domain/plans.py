"""Untrusted plan-proposal contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from handsoff.domain import (
    ContractModel,
    ContractVersion,
    Identifier,
    UtcDateTime,
)
from handsoff.domain.capabilities import AutonomyMode  # noqa: TC001
from handsoff.domain.goals import AcceptanceCondition  # noqa: TC001


class FailureStrategy(StrEnum):
    """Plan behavior proposed after an action failure."""

    STOP = "stop"
    CONTINUE = "continue"
    COMPENSATE = "compensate"


class PlannedAction(ContractModel):
    """One proposed use of a declared capability."""

    action_id: Identifier
    capability_id: Identifier
    capability_version: ContractVersion
    target_entity_id: Identifier
    parameters: dict[Identifier, JsonValue]
    depends_on: tuple[Identifier, ...] = ()
    preconditions: tuple[AcceptanceCondition, ...] = ()
    acceptance_conditions: Annotated[tuple[AcceptanceCondition, ...], Field(min_length=1)]
    idempotency_key: Identifier
    on_failure: FailureStrategy

    @model_validator(mode="after")
    def validate_action(self) -> Self:
        """Require unique dependency and condition identifiers."""
        if len(self.depends_on) != len(set(self.depends_on)):
            message = "action dependencies must be unique"
            raise ValueError(message)
        condition_ids = [condition.condition_id for condition in self.acceptance_conditions]
        if len(condition_ids) != len(set(condition_ids)):
            message = "action acceptance condition identifiers must be unique"
            raise ValueError(message)
        return self


class PlanProposal(ContractModel):
    """A schema-valid but not yet authorized proposed plan."""

    plan_id: Identifier
    schema_version: ContractVersion
    goal_id: Identifier
    created_at: UtcDateTime
    expires_at: UtcDateTime
    mode: AutonomyMode
    planner_id: Identifier
    planner_version: ContractVersion
    world_state_observation_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    actions: Annotated[tuple[PlannedAction, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        """Require unique references, valid dependencies, and an acyclic graph."""
        self._validate_plan_identity()
        self._validate_dependency_graph()
        return self

    def _validate_plan_identity(self) -> None:
        """Require temporal ordering and unique identifiers."""
        if self.expires_at <= self.created_at:
            message = "plan expiration must be later than creation"
            raise ValueError(message)

        observation_ids = self.world_state_observation_ids
        if len(observation_ids) != len(set(observation_ids)):
            message = "world-state observation identifiers must be unique"
            raise ValueError(message)

        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            message = "action identifiers must be unique"
            raise ValueError(message)

        idempotency_keys = [action.idempotency_key for action in self.actions]
        if len(idempotency_keys) != len(set(idempotency_keys)):
            message = "action idempotency keys must be unique"
            raise ValueError(message)

    def _validate_dependency_graph(self) -> None:
        """Require declared, non-self, acyclic action dependencies."""
        action_ids = [action.action_id for action in self.actions]
        known_action_ids = set(action_ids)
        unresolved: dict[str, set[str]] = {}
        for action in self.actions:
            dependencies = set(action.depends_on)
            if action.action_id in dependencies:
                message = "an action cannot depend on itself"
                raise ValueError(message)
            if not dependencies <= known_action_ids:
                message = "action dependency references an undeclared action"
                raise ValueError(message)
            unresolved[action.action_id] = dependencies

        resolved: set[str] = set()
        while unresolved:
            ready = {action_id for action_id, deps in unresolved.items() if deps <= resolved}
            if not ready:
                message = "action dependency graph must be acyclic"
                raise ValueError(message)
            resolved.update(ready)
            for action_id in ready:
                del unresolved[action_id]


__all__ = ["FailureStrategy", "PlanProposal", "PlannedAction"]
