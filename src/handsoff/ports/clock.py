"""Time-source port used by deterministic domain and application services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime


@runtime_checkable
class Clock(Protocol):
    """Return the current aware UTC time."""

    def now(self) -> datetime:
        """Return the current time."""
        raise NotImplementedError


__all__ = ["Clock"]
