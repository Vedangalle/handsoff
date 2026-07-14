"""Reproducible execution of committed deterministic scenario fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from handsoff.adapters.devices.simulator import ScriptedSimulatorAdapter
from handsoff.adapters.memory import NoopMemoryProvider
from handsoff.adapters.persistence.memory import InMemoryLedger
from handsoff.adapters.planner import DeterministicPlanner
from handsoff.application.capability_registry import CapabilityRegistry
from handsoff.application.compile_goal import GoalCompiler
from handsoff.application.execute_plan import PlanExecutor, RuntimeResult
from handsoff.application.world_model import WorldModel
from handsoff.domain.capabilities import AutonomyMode
from handsoff.domain.scenarios import ScenarioDefinition

if TYPE_CHECKING:
    from pathlib import Path

    from handsoff.ports.memory import MemoryProvider
    from handsoff.ports.planner import Planner
    from handsoff.ports.repositories import LedgerRepository


@dataclass(frozen=True, slots=True)
class ScenarioAssessment:
    """Observed result compared with the committed expected test vector."""

    scenario_id: str
    matched: bool
    mismatches: tuple[str, ...]
    runtime: RuntimeResult


def load_scenario(path: Path) -> ScenarioDefinition:
    """Load YAML as untrusted data through the strict scenario schema."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ScenarioDefinition.model_validate_json(json.dumps(raw))


class ScenarioRunner:
    """Compose deterministic ports and adapters for one fixture."""

    def __init__(
        self,
        planner: Planner | None = None,
        memory: MemoryProvider | None = None,
        ledger: LedgerRepository | None = None,
        memory_scope: str | None = None,
    ) -> None:
        """Compose provider-independent defaults with optional test overrides."""
        self._planner = planner or DeterministicPlanner()
        self._memory = memory or NoopMemoryProvider()
        self._ledger = ledger or InMemoryLedger()
        self._memory_scope = memory_scope

    def run(self, scenario: ScenarioDefinition) -> ScenarioAssessment:
        """Execute and compare all deterministic acceptance evidence."""
        world = WorldModel(scenario.initial_observations)
        registry = CapabilityRegistry(scenario.capabilities)
        planner_result = GoalCompiler(self._planner, self._memory).compile(
            goal=scenario.goal,
            observations=world.observations(),
            capabilities=registry.contracts(),
            mode=AutonomyMode.SIMULATION,
            now=scenario.clock_start_at,
            memory_scope=self._memory_scope or scenario.scenario_id,
        )
        runtime = PlanExecutor(
            registry=registry,
            world=world,
            adapter=ScriptedSimulatorAdapter(scenario.scripted_outcomes),
            ledger=self._ledger,
        ).run(scenario.goal, planner_result, scenario.clock_start_at)
        mismatches = self.compare(scenario, runtime)
        return ScenarioAssessment(
            scenario_id=scenario.scenario_id,
            matched=not mismatches,
            mismatches=mismatches,
            runtime=runtime,
        )

    @staticmethod
    def compare(
        scenario: ScenarioDefinition,
        runtime: RuntimeResult,
    ) -> tuple[str, ...]:
        """Compare every observable runtime outcome with a fixture vector."""
        expected = scenario.expected
        mismatches: list[str] = []
        if runtime.policy.decision is not expected.policy_decision:
            mismatches.append("policy decision differs from fixture")
        if runtime.terminal_plan_state is not expected.terminal_plan_state:
            mismatches.append("terminal plan state differs from fixture")
        if set(runtime.dispatched_capability_ids) != set(expected.dispatched_capability_ids):
            mismatches.append("dispatched capability set differs from fixture")
        if set(runtime.withheld_capability_ids) != set(expected.withheld_capability_ids):
            mismatches.append("withheld capability set differs from fixture")
        verified = {result.condition_id for result in runtime.verifications if result.satisfied}
        unsatisfied = {
            result.condition_id for result in runtime.verifications if not result.satisfied
        }
        if verified != set(expected.verified_condition_ids):
            mismatches.append("verified condition set differs from fixture")
        if unsatisfied != set(expected.unsatisfied_condition_ids):
            mismatches.append("unsatisfied condition set differs from fixture")
        return tuple(mismatches)


__all__ = ["ScenarioAssessment", "ScenarioRunner", "load_scenario"]
