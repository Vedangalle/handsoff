"""Script-driven simulator with duplicate-effect suppression."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.ports.capability_adapter import DispatchResult, DispatchStatus

if TYPE_CHECKING:
    from handsoff.domain.capabilities import CapabilityContract
    from handsoff.domain.plans import PlannedAction
    from handsoff.domain.scenarios import ScriptedCapabilityOutcome


class ScriptedSimulatorAdapter:
    """Return only scenario-declared outcomes and apply each key at most once."""

    def __init__(self, outcomes: tuple[ScriptedCapabilityOutcome, ...]) -> None:
        """Index scripted outcomes by capability and bounded attempt."""
        self._outcomes = {(outcome.capability_id, outcome.attempt): outcome for outcome in outcomes}
        self._completed: dict[str, DispatchResult] = {}

    def dispatch(
        self,
        action: PlannedAction,
        capability: CapabilityContract,
        attempt: int,
    ) -> DispatchResult:
        """Execute one deterministic attempt without any real actuation."""
        if action.capability_id != capability.capability_id:
            message = "action and capability identifiers do not match"
            raise ValueError(message)
        prior = self._completed.get(action.idempotency_key)
        if prior is not None:
            return DispatchResult(
                status=prior.status,
                observations=(),
                reason="duplicate idempotency key suppressed",
                duplicate=True,
            )

        scripted = self._outcomes.get((capability.capability_id, attempt))
        if scripted is None:
            result = DispatchResult(
                status=DispatchStatus.FAILED,
                observations=(),
                reason="no scripted outcome exists for this attempt",
            )
        else:
            result = DispatchResult(
                status=DispatchStatus(scripted.result.value),
                observations=scripted.effect_observations,
                reason=f"scripted simulator returned {scripted.result.value}",
            )
        if result.status in {DispatchStatus.ADAPTER_ACCEPTED, DispatchStatus.EFFECT_OBSERVED}:
            self._completed[action.idempotency_key] = result
        return result


__all__ = ["ScriptedSimulatorAdapter"]
