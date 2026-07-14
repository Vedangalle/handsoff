"""Operational-ledger event contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from handsoff.domain.events import EventKind, FailureRecord, LedgerEvent
from handsoff.domain.goals import Goal
from tests.fixtures.contracts import NOW, make_goal


def test_ledger_event_carries_typed_payload() -> None:
    """A specialized event envelope preserves its domain payload type."""
    event = LedgerEvent(
        event_id="event.goal-received",
        stream_id="goal.arrival",
        sequence_number=1,
        kind=EventKind.GOAL_RECEIVED,
        occurred_at=NOW,
        correlation_id="correlation.arrival",
        payload=make_goal(),
    )
    assert isinstance(event.payload, Goal)
    assert event.payload.goal_id == "goal.arrival"


def test_event_rejects_self_causation() -> None:
    """An append-only event cannot identify itself as its cause."""
    with pytest.raises(ValidationError, match="cannot cause itself"):
        LedgerEvent(
            event_id="event.goal-received",
            stream_id="goal.arrival",
            sequence_number=1,
            kind=EventKind.GOAL_RECEIVED,
            occurred_at=NOW,
            correlation_id="correlation.arrival",
            causation_event_id="event.goal-received",
            payload=make_goal(),
        )


def test_failure_record_contains_structured_nonsecret_evidence() -> None:
    """Failure evidence uses codes and summaries rather than raw exception payloads."""
    failure = FailureRecord(
        failure_code="adapter.timeout",
        summary="The simulated adapter exceeded its bounded timeout",
        retryable=True,
        subject_id="action.prepare",
    )
    assert failure.retryable


def test_event_rejects_kind_payload_mismatch() -> None:
    """Ledger evidence cannot label a goal payload as a failure."""
    with pytest.raises(ValidationError, match="payload type does not match"):
        LedgerEvent(
            event_id="event.mislabeled",
            stream_id="goal.arrival",
            sequence_number=1,
            kind=EventKind.FAILURE_RECORDED,
            occurred_at=NOW,
            correlation_id="correlation.arrival",
            payload=make_goal(),
        )
