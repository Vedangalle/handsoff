"""Bounded capability-dispatch port."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from handsoff.domain.capabilities import CapabilityContract
    from handsoff.domain.observations import Observation
    from handsoff.domain.plans import PlannedAction


class DispatchStatus(StrEnum):
    """Evidence level returned by a capability adapter."""

    ADAPTER_ACCEPTED = "adapter_accepted"
    EFFECT_OBSERVED = "effect_observed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """One bounded adapter attempt; acceptance is not verification."""

    status: DispatchStatus
    observations: tuple[Observation, ...]
    reason: str
    duplicate: bool = False


@runtime_checkable
class CapabilityAdapter(Protocol):
    """Execute only a previously authorized typed capability."""

    def dispatch(
        self,
        action: PlannedAction,
        capability: CapabilityContract,
        attempt: int,
    ) -> DispatchResult:
        """Attempt one action with a bounded retry number."""
        ...


__all__ = ["CapabilityAdapter", "DispatchResult", "DispatchStatus"]
