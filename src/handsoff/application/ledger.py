"""Deterministic construction of append-only evidence envelopes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.domain.events import EventKind, EventPayload, LedgerEvent

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.ports.repositories import LedgerRepository


class LedgerRecorder:
    """Assign stable stream sequence numbers and causation links."""

    def __init__(self, repository: LedgerRepository, stream_id: str) -> None:
        """Bind a repository and one immutable stream identity."""
        self._repository = repository
        self._stream_id = stream_id
        self._last_event_id: str | None = None

    def record(
        self,
        kind: EventKind,
        payload: EventPayload,
        occurred_at: datetime,
    ) -> LedgerEvent:
        """Append one event caused by the previous event in the stream."""
        sequence = len(self._repository.list_stream(self._stream_id)) + 1
        suffix = self._stream_id.replace(".", "-")
        event = LedgerEvent(
            event_id=f"event.{suffix}.{sequence}",
            stream_id=self._stream_id,
            sequence_number=sequence,
            kind=kind,
            occurred_at=occurred_at,
            correlation_id=f"correlation.{suffix}",
            causation_event_id=self._last_event_id,
            payload=payload,
        )
        self._repository.append(event)
        self._last_event_id = event.event_id
        return event


__all__ = ["LedgerRecorder"]
