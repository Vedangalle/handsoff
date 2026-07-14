"""Provider-independent plan proposal boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.domain.capabilities import AutonomyMode, CapabilityContract
    from handsoff.domain.goals import Goal
    from handsoff.domain.observations import Observation
    from handsoff.domain.plans import PlanProposal


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    """Complete trusted input available to a planner adapter."""

    goal: Goal
    observations: tuple[Observation, ...]
    capabilities: tuple[CapabilityContract, ...]
    mode: AutonomyMode
    now: datetime
    preference_context: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PlannerResult:
    """Plan plus measured provider provenance."""

    plan: PlanProposal
    provider: str
    model: str
    used_fallback: bool
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class Planner(Protocol):
    """Produce an untrusted typed proposal without action authority."""

    def propose(self, request: PlannerRequest) -> PlannerResult:
        """Return a schema-valid plan proposal."""
        ...


__all__ = ["Planner", "PlannerRequest", "PlannerResult"]
