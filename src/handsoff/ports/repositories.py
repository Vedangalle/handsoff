"""Persistence ports for append-only operational evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from handsoff.domain.events import LedgerEvent


@runtime_checkable
class LedgerRepository(Protocol):
    """Append and replay immutable, sequenced ledger events."""

    def append(self, event: LedgerEvent) -> None:
        """Atomically append one event."""
        ...

    def list_stream(self, stream_id: str) -> tuple[LedgerEvent, ...]:
        """Return one stream in sequence order."""
        ...


__all__ = ["LedgerRepository"]
