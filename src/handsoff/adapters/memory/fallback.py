"""Fail-closed semantic-memory composition and non-secret status reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.ports.memory import MemoryItem, MemoryProvider


@dataclass(frozen=True, slots=True)
class MemoryRetrievalReport:
    """Safe evidence about the most recent optional-memory retrieval."""

    provider: str
    scope: str
    used_fallback: bool
    items: tuple[MemoryItem, ...]
    failure_code: str | None = None


class ResilientMemoryProvider:
    """Use empty local context when an external memory provider fails."""

    def __init__(self, primary: MemoryProvider, fallback: MemoryProvider, provider: str) -> None:
        """Bind one external provider and a provider-disabled fallback."""
        self._primary = primary
        self._fallback = fallback
        self._provider = provider
        self._last_report: MemoryRetrievalReport | None = None

    @property
    def last_report(self) -> MemoryRetrievalReport | None:
        """Return bounded status without an exception message or credential material."""
        return self._last_report

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Retrieve external context or fail closed to the local empty provider."""
        try:
            items = self._primary.retrieve(query, scope, limit)
        except Exception:  # noqa: BLE001 - provider failures must preserve offline operation
            items = self._fallback.retrieve(query, scope, limit)
            self._last_report = MemoryRetrievalReport(
                provider=self._provider,
                scope=scope,
                used_fallback=True,
                items=items,
                failure_code="memory_provider_unavailable",
            )
            return items
        self._last_report = MemoryRetrievalReport(
            provider=self._provider,
            scope=scope,
            used_fallback=False,
            items=items,
        )
        return items


__all__ = ["MemoryRetrievalReport", "ResilientMemoryProvider"]
