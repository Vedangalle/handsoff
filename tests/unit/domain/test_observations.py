"""World-observation contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from handsoff.domain.observations import ObservationQuality
from tests.fixtures.contracts import make_observation


def test_observation_preserves_provenance_and_quality() -> None:
    """A normalized observation carries explicit source and quality evidence."""
    observation = make_observation(unit="state")
    assert observation.source_adapter_id == "adapter.simulator"
    assert observation.quality is ObservationQuality.NOMINAL


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("inf"), float("nan")])
def test_observation_rejects_invalid_confidence(confidence: float) -> None:
    """Confidence is finite and bounded to the closed unit interval."""
    with pytest.raises(ValidationError):
        make_observation(confidence=confidence)


@pytest.mark.parametrize("freshness", [0.0, -1.0, float("inf"), float("nan")])
def test_observation_rejects_invalid_freshness(freshness: float) -> None:
    """Freshness limits are finite positive durations."""
    with pytest.raises(ValidationError):
        make_observation(freshness_limit_seconds=freshness)


def test_observation_rejects_naive_timestamp() -> None:
    """Boundary timestamps require timezone awareness."""
    with pytest.raises(ValidationError):
        make_observation(observed_at=datetime(2026, 7, 13, 12, 0))  # noqa: DTZ001


def test_observation_rejects_non_utc_timestamp() -> None:
    """Aware non-UTC timestamps are rejected rather than normalized silently."""
    non_utc = datetime(2026, 7, 13, 12, 0, tzinfo=timezone(timedelta(hours=-7)))
    with pytest.raises(ValidationError, match="timestamp must use UTC"):
        make_observation(observed_at=non_utc)


def test_observation_accepts_explicit_utc() -> None:
    """An explicit UTC timestamp satisfies the temporal boundary."""
    observed_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    assert make_observation(observed_at=observed_at).observed_at == observed_at
