"""Optional context-only semantic-memory boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Minimized untrusted context retrieved from an external provider."""

    source_id: str
    text: str
    relevance: float


@runtime_checkable
class MemoryProvider(Protocol):
    """Retrieve context that cannot grant authority or verify an outcome."""

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Return bounded context for planner input only."""
        ...


__all__ = ["MemoryItem", "MemoryProvider"]
