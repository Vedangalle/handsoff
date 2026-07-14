"""Provider-disabled semantic-memory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.ports.memory import MemoryItem


class NoopMemoryProvider:
    """Preserve full core behavior when semantic memory is disabled."""

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Return no external context."""
        del query, scope, limit
        return ()


__all__ = ["NoopMemoryProvider"]
