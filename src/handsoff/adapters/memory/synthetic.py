"""Deterministic synthetic context for credential-free demonstrations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.ports.memory import MemoryItem

if TYPE_CHECKING:
    from collections.abc import Sequence


_SYNTHETIC_ITEMS: tuple[MemoryItem, ...] = (
    MemoryItem(
        source_id="synthetic.preference.arrival-comfort",
        text=(
            "Synthetic preference: target a calm arrival environment; prepare climate and media, "
            "but never start playback automatically."
        ),
        relevance=0.96,
    ),
    MemoryItem(
        source_id="synthetic.preference.energy",
        text=(
            "Synthetic preference: honor an active demand-response event and accept the declared "
            "economy setpoint instead of overriding the grid constraint."
        ),
        relevance=0.91,
    ),
    MemoryItem(
        source_id="synthetic.preference.safety",
        text=(
            "Synthetic preference: garage preparation is acceptable only when destination evidence "
            "is fresh and obstruction telemetry is clear."
        ),
        relevance=0.88,
    ),
)


class SyntheticMemoryProvider:
    """Return fixed local fixtures through the same bounded memory port."""

    def __init__(self, items: Sequence[MemoryItem] = _SYNTHETIC_ITEMS) -> None:
        """Copy immutable fixture items so callers cannot mutate shared state."""
        self._items = tuple(items)

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Return a bounded deterministic result without network or credentials."""
        del query, scope
        if limit < 0:
            message = "memory result limit cannot be negative"
            raise ValueError(message)
        return self._items[:limit]


__all__ = ["SyntheticMemoryProvider"]
