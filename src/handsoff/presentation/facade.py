"""Provider-contained application facade for the public demonstration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from handsoff.adapters.memory import (
    MemoryRetrievalReport,
    NoopMemoryProvider,
    ResilientMemoryProvider,
    SupermemoryMemoryProvider,
    SyntheticMemoryProvider,
)
from handsoff.adapters.persistence.memory import InMemoryLedger
from handsoff.adapters.planner import DeterministicPlanner, FallbackPlanner, GeminiPlanner
from handsoff.adapters.planner.gemini import GoogleGenAITransport
from handsoff.application.run_scenario import ScenarioAssessment, ScenarioRunner, load_scenario

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from handsoff.domain.scenarios import ScenarioDefinition
    from handsoff.ports.memory import MemoryItem
    from handsoff.ports.planner import Planner, PlannerRequest, PlannerResult
    from handsoff.presentation.config import DemoSettings


class DemoMode(StrEnum):
    """Explicit provider combinations available to a public browser session."""

    DETERMINISTIC = "deterministic"
    SYNTHETIC_MEMORY = "synthetic_memory"
    GEMINI = "gemini"
    GEMINI_SUPERMEMORY = "gemini_supermemory"

    @property
    def label(self) -> str:
        """Return a concise operator-facing mode name."""
        return {
            DemoMode.DETERMINISTIC: "Deterministic baseline",
            DemoMode.SYNTHETIC_MEMORY: "Offline memory lab",
            DemoMode.GEMINI: "Gemini planner",
            DemoMode.GEMINI_SUPERMEMORY: "Gemini + Supermemory context",
        }[self]


@dataclass(frozen=True, slots=True)
class ScenarioOption:
    """Allowlisted scenario metadata safe for selection in the browser."""

    scenario_id: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class DemoRun:
    """Complete inspectable output returned to a presentation adapter."""

    mode: DemoMode
    scenario: ScenarioDefinition
    assessment: ScenarioAssessment
    memory: MemoryRetrievalReport
    trusted_input_fingerprint: str


class _UnavailablePlanner:
    """Trigger deterministic fallback when Gemini is not configured."""

    def propose(self, request: PlannerRequest) -> PlannerResult:
        """Fail without performing external work."""
        del request
        message = "Gemini provider is not configured"
        raise RuntimeError(message)


class _UnavailableMemoryProvider:
    """Trigger empty-context fallback when Supermemory is not configured."""

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Fail without performing external work."""
        del query, scope, limit
        message = "Supermemory provider is not configured"
        raise RuntimeError(message)


class DemoFacade:
    """Load committed fixtures and compose one isolated runtime per run."""

    def __init__(self, settings: DemoSettings, scenarios_dir: Path) -> None:
        """Bind server settings and an allowlisted committed scenario directory."""
        self._settings = settings
        paths = sorted(scenarios_dir.glob("*.yaml"))
        scenarios = tuple(load_scenario(path) for path in paths)
        if not scenarios:
            message = "no committed scenarios were found"
            raise ValueError(message)
        if len({scenario.scenario_id for scenario in scenarios}) != len(scenarios):
            message = "scenario identifiers must be unique"
            raise ValueError(message)
        self._scenarios = {scenario.scenario_id: scenario for scenario in scenarios}

    @property
    def settings(self) -> DemoSettings:
        """Return presence-only provider configuration properties to the UI."""
        return self._settings

    def scenarios(self) -> tuple[ScenarioOption, ...]:
        """Return the fixed committed scenario selection."""
        return tuple(
            ScenarioOption(scenario.scenario_id, scenario.title, scenario.description)
            for scenario in self._scenarios.values()
        )

    def scenario(self, scenario_id: str) -> ScenarioDefinition:
        """Return one committed scenario contract for presentation-only framing."""
        try:
            return self._scenarios[scenario_id]
        except KeyError as error:
            message = "scenario is not in the committed allowlist"
            raise ValueError(message) from error

    def run(self, scenario_id: str, mode: DemoMode) -> DemoRun:
        """Execute one scenario with fresh per-run adapters, world, and ledger."""
        scenario = self.scenario(scenario_id)

        planner, close_planner = self._planner(mode)
        memory, reporter = self._memory(mode)
        try:
            assessment = ScenarioRunner(
                planner=planner,
                memory=memory,
                ledger=InMemoryLedger(),
                memory_scope=self._settings.memory_scope,
            ).run(scenario)
        finally:
            if close_planner is not None:
                close_planner()

        report = (
            reporter.last_report
            if reporter is not None
            else MemoryRetrievalReport(
                provider="disabled",
                scope=self._settings.memory_scope,
                used_fallback=False,
                items=(),
            )
        )
        if report is None:
            message = "memory provider did not produce a retrieval report"
            raise RuntimeError(message)
        return DemoRun(
            mode=mode,
            scenario=scenario,
            assessment=assessment,
            memory=report,
            trusted_input_fingerprint=self._trusted_fingerprint(scenario),
        )

    def _planner(self, mode: DemoMode) -> tuple[Planner, Callable[[], None] | None]:
        """Compose deterministic or contained Gemini planning with fallback."""
        fallback = DeterministicPlanner()
        if mode in {DemoMode.DETERMINISTIC, DemoMode.SYNTHETIC_MEMORY}:
            return fallback, None
        if not self._settings.google_api_key:
            return FallbackPlanner(_UnavailablePlanner(), fallback), None
        transport = GoogleGenAITransport(self._settings.google_api_key)
        primary = GeminiPlanner(transport, model=self._settings.gemini_model)
        return FallbackPlanner(primary, fallback), transport.close

    def _memory(
        self,
        mode: DemoMode,
    ) -> tuple[NoopMemoryProvider | ResilientMemoryProvider, ResilientMemoryProvider | None]:
        """Compose fixed-scope read-only memory or a provider-disabled adapter."""
        fallback = NoopMemoryProvider()
        if mode is DemoMode.SYNTHETIC_MEMORY:
            provider = ResilientMemoryProvider(
                SyntheticMemoryProvider(),
                fallback,
                "synthetic",
            )
            return provider, provider
        if mode is not DemoMode.GEMINI_SUPERMEMORY:
            return fallback, None
        primary = (
            SupermemoryMemoryProvider(
                api_key=self._settings.supermemory_api_key,
                scope=self._settings.memory_scope,
            )
            if self._settings.supermemory_api_key
            else _UnavailableMemoryProvider()
        )
        provider = ResilientMemoryProvider(primary, fallback, "supermemory")
        return provider, provider

    @staticmethod
    def _trusted_fingerprint(scenario: ScenarioDefinition) -> str:
        """Fingerprint authority inputs while excluding memory and provider output."""
        payload = {
            "goal": scenario.goal.model_dump(mode="json"),
            "observations": [
                observation.model_dump(mode="json") for observation in scenario.initial_observations
            ],
            "capabilities": [
                capability.model_dump(mode="json") for capability in scenario.capabilities
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


__all__ = ["DemoFacade", "DemoMode", "DemoRun", "ScenarioOption"]
