"""Property-based checks for contract boundary invariants."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from handsoff.adapters.clock import DeterministicClock
from tests.fixtures.contracts import NOW, make_observation


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
def test_every_finite_unit_interval_confidence_is_valid(confidence: float) -> None:
    """The complete valid confidence domain is accepted."""
    assert make_observation(confidence=confidence).confidence == confidence


@given(
    st.floats(allow_nan=False, allow_infinity=False).filter(
        lambda value: value < 0.0 or value > 1.0
    )
)
def test_every_finite_out_of_range_confidence_is_rejected(confidence: float) -> None:
    """Every finite confidence outside the unit interval is rejected."""
    try:
        make_observation(confidence=confidence)
    except ValidationError:
        return
    msg = "out-of-range confidence unexpectedly validated"
    raise AssertionError(msg)


@given(st.integers(min_value=0, max_value=86_400))
def test_clock_advance_is_exact_for_nonnegative_seconds(seconds: int) -> None:
    """The deterministic clock adds exactly the supplied duration."""
    clock = DeterministicClock(NOW)
    assert clock.advance(timedelta(seconds=seconds)) == NOW + timedelta(seconds=seconds)
