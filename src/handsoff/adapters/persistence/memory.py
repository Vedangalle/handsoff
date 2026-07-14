"""In-memory append-only ledger for isolated tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.domain.events import LedgerEvent


class InMemoryLedger:
    """Append-only event storage with stream sequence enforcement."""

    def __init__(self) -> None:
        """Initialize empty independent streams."""
        self._events: dict[str, list[LedgerEvent]] = {}
        self._event_ids: set[str] = set()

    def append(self, event: LedgerEvent) -> None:
        """Append exactly the next event for a stream."""
        if event.event_id in self._event_ids:
            message = "ledger event identifier already exists"
            raise ValueError(message)
        stream = self._events.setdefault(event.stream_id, [])
        if event.sequence_number != len(stream) + 1:
            message = "ledger sequence number is not the next stream position"
            raise ValueError(message)
        stream.append(event)
        self._event_ids.add(event.event_id)

    def list_stream(self, stream_id: str) -> tuple[LedgerEvent, ...]:
        """Replay immutable events in sequence order."""
        return tuple(self._events.get(stream_id, ()))


__all__ = ["InMemoryLedger"]
