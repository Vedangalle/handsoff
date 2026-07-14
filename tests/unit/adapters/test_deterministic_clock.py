"""Deterministic clock adapter tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from handsoff.adapters.clock import DeterministicClock
from handsoff.ports.clock import Clock
from tests.fixtures.contracts import NOW


def read_clock(clock: Clock) -> datetime:
    """Exercise the clock through its port."""
    return clock.now()


def test_clock_satisfies_port_and_advances_deterministically() -> None:
    """Time advances only by the explicitly supplied duration."""
    clock = DeterministicClock(NOW)
    assert isinstance(clock, Clock)
    assert read_clock(clock) == NOW
    assert clock.advance(timedelta(seconds=5)) == NOW + timedelta(seconds=5)
    assert clock.advance(timedelta(0)) == NOW + timedelta(seconds=5)


def test_clock_rejects_naive_initial_time() -> None:
    """The test clock cannot begin from an ambiguous naive timestamp."""
    with pytest.raises(ValueError, match="aware UTC"):
        DeterministicClock(datetime(2026, 7, 13, 12, 0))  # noqa: DTZ001


def test_clock_rejects_non_utc_initial_time() -> None:
    """The test clock requires explicit UTC rather than silent conversion."""
    local_time = datetime(
        2026,
        7,
        13,
        12,
        0,
        tzinfo=timezone(timedelta(hours=-7)),
    )
    with pytest.raises(ValueError, match="aware UTC"):
        DeterministicClock(local_time)


def test_clock_cannot_move_backward() -> None:
    """Replay time is monotonic."""
    clock = DeterministicClock(NOW)
    with pytest.raises(ValueError, match="cannot move backward"):
        clock.advance(timedelta(microseconds=-1))
