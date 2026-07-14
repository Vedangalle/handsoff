"""Goal compilation with bounded optional preference context."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.ports.planner import Planner, PlannerRequest, PlannerResult

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.domain.capabilities import AutonomyMode, CapabilityContract
    from handsoff.domain.goals import Goal
    from handsoff.domain.observations import Observation
    from handsoff.ports.memory import MemoryProvider


class GoalCompiler:
    """Retrieve untrusted context and request a typed plan proposal."""

    def __init__(self, planner: Planner, memory: MemoryProvider) -> None:
        """Bind replaceable planner and memory ports."""
        self._planner = planner
        self._memory = memory

    def compile(  # noqa: PLR0913 - explicit trust-boundary inputs remain named
        self,
        goal: Goal,
        observations: tuple[Observation, ...],
        capabilities: tuple[CapabilityContract, ...],
        mode: AutonomyMode,
        now: datetime,
        memory_scope: str,
    ) -> PlannerResult:
        """Compile without allowing memory content to change authority."""
        items = self._memory.retrieve(goal.objective, memory_scope, 5)
        context = tuple(
            normalized for item in items if (normalized := " ".join(item.text.split())[:500])
        )
        request = PlannerRequest(
            goal=goal,
            observations=observations,
            capabilities=capabilities,
            mode=mode,
            now=now,
            preference_context=context,
        )
        return self._planner.propose(request)


__all__ = ["GoalCompiler"]
