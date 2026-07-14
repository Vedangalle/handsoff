"""Fail-closed planner composition with deterministic availability."""

from __future__ import annotations

from handsoff.ports.planner import Planner, PlannerRequest, PlannerResult


class FallbackPlanner:
    """Use a deterministic planner whenever an external planner fails."""

    def __init__(self, primary: Planner, fallback: Planner) -> None:
        """Bind the provider planner and offline fallback."""
        self._primary = primary
        self._fallback = fallback

    def propose(self, request: PlannerRequest) -> PlannerResult:
        """Return primary output or a marked deterministic fallback result."""
        try:
            return self._primary.propose(request)
        except Exception:  # noqa: BLE001 - provider failure is an explicit fallback boundary
            fallback = self._fallback.propose(request)
            return PlannerResult(
                plan=fallback.plan,
                provider=fallback.provider,
                model=fallback.model,
                used_fallback=True,
                latency_ms=fallback.latency_ms,
                input_tokens=fallback.input_tokens,
                output_tokens=fallback.output_tokens,
            )


__all__ = ["FallbackPlanner"]
