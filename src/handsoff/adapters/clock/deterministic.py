"""Manually advanced deterministic clock for tests and scenario replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


def _validate_utc(value: datetime) -> None:
    """Require an aware UTC datetime."""
    if value.utcoffset() != timedelta(0):
        message = "deterministic clock requires an aware UTC datetime"
        raise ValueError(message)


@dataclass(slots=True)
class DeterministicClock:
    """A monotonic, explicitly advanced clock with no wall-clock dependency."""

    _current: datetime

    def __post_init__(self) -> None:
        """Validate the initial timestamp."""
        _validate_utc(self._current)

    def now(self) -> datetime:
        """Return the configured deterministic time."""
        return self._current

    def advance(self, delta: timedelta) -> datetime:
        """Advance by a non-negative duration and return the new time."""
        if delta < timedelta(0):
            message = "deterministic clock cannot move backward"
            raise ValueError(message)
        self._current += delta
        return self._current


__all__ = ["DeterministicClock"]
