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
            "Synthetic preference: for the evening homecoming routine, use welcome lighting, "
            "set the fan low, and resume Orbit Seven after arrival confidence clears policy."
        ),
        relevance=0.96,
    ),
    MemoryItem(
        source_id="synthetic.preference.kitchen",
        text=(
            "Synthetic preference: keep ice production ready and brew arrival coffee only when "
            "the water reservoir and cup sensors both report available."
        ),
        relevance=0.94,
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
