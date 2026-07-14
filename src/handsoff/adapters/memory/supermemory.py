"""Bounded read-only Supermemory search adapter."""

from __future__ import annotations

import math
import re
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, JsonValue

from handsoff.ports.memory import MemoryItem

SUPERMEMORY_SEARCH_URL = "https://api.supermemory.ai/v4/search"
MAX_MEMORY_ITEMS = 5
MAX_MEMORY_TEXT_LENGTH = 500
MAX_QUERY_LENGTH = 1_000
_SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9_:-]{1,100}$")


class _SearchResponse(BaseModel):
    """Minimal response envelope; provider content remains untrusted JSON."""

    model_config = ConfigDict(extra="ignore", strict=True)

    results: list[dict[str, JsonValue]]


class SupermemorySearchTransport(Protocol):
    """Narrow read-only transport seam used for tests and HTTP isolation."""

    def search(
        self,
        *,
        api_key: str,
        query: str,
        scope: str,
        limit: int,
    ) -> object:
        """Return an untrusted decoded search response."""
        ...


class HttpxSupermemoryTransport:
    """Call only Supermemory's fixed v4 search endpoint."""

    def search(
        self,
        *,
        api_key: str,
        query: str,
        scope: str,
        limit: int,
    ) -> object:
        """Perform one bounded hybrid search without exposing a write method."""
        response = httpx.post(
            SUPERMEMORY_SEARCH_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "q": query,
                "containerTag": scope,
                "limit": limit,
                "searchMode": "hybrid",
                "rerank": False,
                "aggregate": False,
                "rewriteQuery": False,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json()


class SupermemoryMemoryProvider:
    """Normalize untrusted Supermemory results into context-only memory items."""

    def __init__(
        self,
        api_key: str,
        scope: str,
        transport: SupermemorySearchTransport | None = None,
    ) -> None:
        """Bind a credential and immutable server-configured demo scope."""
        if not api_key:
            message = "Supermemory API key must be supplied explicitly"
            raise ValueError(message)
        if _SCOPE_PATTERN.fullmatch(scope) is None:
            message = "Supermemory scope must be a bounded container tag"
            raise ValueError(message)
        self._api_key = api_key
        self._scope = scope
        self._transport = transport or HttpxSupermemoryTransport()

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Search the bound scope and return at most five normalized items."""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            message = "Supermemory query cannot be blank"
            raise ValueError(message)
        if len(normalized_query) > MAX_QUERY_LENGTH:
            message = "Supermemory query exceeds the maximum length"
            raise ValueError(message)
        if scope != self._scope:
            message = "requested memory scope does not match the configured scope"
            raise ValueError(message)
        if not 1 <= limit <= MAX_MEMORY_ITEMS:
            message = "Supermemory result limit must be between one and five"
            raise ValueError(message)

        raw = self._transport.search(
            api_key=self._api_key,
            query=normalized_query,
            scope=self._scope,
            limit=limit,
        )
        response = _SearchResponse.model_validate(raw)
        items = [item for raw_item in response.results if (item := self._to_item(raw_item))]
        return tuple(items[:limit])

    @staticmethod
    def _to_item(raw: dict[str, JsonValue]) -> MemoryItem | None:
        """Extract only bounded source, text, and relevance fields."""
        text = SupermemoryMemoryProvider._extract_text(raw)
        if not text:
            return None
        return MemoryItem(
            source_id=SupermemoryMemoryProvider._extract_source(raw),
            text=text,
            relevance=SupermemoryMemoryProvider._extract_relevance(raw),
        )

    @staticmethod
    def _extract_text(raw: dict[str, JsonValue]) -> str:
        """Support memory and chunk result variants without trusting either schema."""
        for key in ("memory", "chunk"):
            value = raw.get(key)
            if isinstance(value, str):
                candidate = value
            elif isinstance(value, dict):
                candidate = next(
                    (
                        nested
                        for field in ("content", "text", "summary")
                        if isinstance((nested := value.get(field)), str)
                    ),
                    "",
                )
            else:
                candidate = ""
            normalized = " ".join(candidate.split())[:MAX_MEMORY_TEXT_LENGTH]
            if normalized:
                return normalized
        return ""

    @staticmethod
    def _extract_source(raw: dict[str, JsonValue]) -> str:
        """Return a bounded opaque provider identifier."""
        for key in ("id", "memoryId", "documentId"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:128]
        for key in ("memory", "chunk"):
            value = raw.get(key)
            if isinstance(value, dict):
                for nested_key in ("id", "memoryId", "documentId"):
                    nested = value.get(nested_key)
                    if isinstance(nested, str) and nested.strip():
                        return nested.strip()[:128]
        return "supermemory-result"

    @staticmethod
    def _extract_relevance(raw: dict[str, JsonValue]) -> float:
        """Normalize finite provider scores to the closed unit interval."""
        candidates: list[JsonValue | None] = [raw.get("score")]
        for key in ("memory", "chunk"):
            value = raw.get(key)
            if isinstance(value, dict):
                candidates.append(value.get("score"))
        for value in candidates:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                score = float(value)
                if math.isfinite(score):
                    return min(1.0, max(0.0, score))
        return 0.0


__all__ = [
    "MAX_MEMORY_ITEMS",
    "MAX_MEMORY_TEXT_LENGTH",
    "SUPERMEMORY_SEARCH_URL",
    "HttpxSupermemoryTransport",
    "SupermemoryMemoryProvider",
    "SupermemorySearchTransport",
]
