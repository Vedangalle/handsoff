"""Read-only Supermemory adapter and fallback tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from handsoff.adapters.memory import NoopMemoryProvider, ResilientMemoryProvider
from handsoff.adapters.memory.supermemory import (
    MAX_MEMORY_TEXT_LENGTH,
    MAX_QUERY_LENGTH,
    SUPERMEMORY_SEARCH_URL,
    HttpxSupermemoryTransport,
    SupermemoryMemoryProvider,
)
from handsoff.ports.memory import MemoryItem

SCOPE = "handsoff-public-demo-v1"
MEMORY_LIMIT = 5
EXPECTED_ITEM_COUNT = 2
HTTP_TIMEOUT_SECONDS = 5.0


class CapturingTransport:
    """Return a controlled search envelope and record bounded arguments."""

    def __init__(self, response: object) -> None:
        """Store one untrusted response."""
        self.response = response
        self.call: dict[str, object] | None = None

    def search(
        self,
        *,
        api_key: str,
        query: str,
        scope: str,
        limit: int,
    ) -> object:
        """Capture arguments without retaining them outside the test double."""
        self.call = {
            "configured": bool(api_key),
            "query": query,
            "scope": scope,
            "limit": limit,
        }
        return self.response


class FailingMemory:
    """External-memory failure double."""

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Fail every request."""
        del query, scope, limit
        message = "downstream unavailable"
        raise RuntimeError(message)


class StaticMemory:
    """Successful-memory double."""

    def retrieve(self, query: str, scope: str, limit: int) -> tuple[MemoryItem, ...]:
        """Return one bounded item."""
        assert query
        assert scope
        assert limit == MEMORY_LIMIT
        return (MemoryItem("source", "prefer economy", 0.9),)


def test_supermemory_normalizes_supported_result_variants() -> None:
    """Only source, bounded text, and finite relevance cross the adapter boundary."""
    long_text = "  prefer   low energy  " * 100
    transport = CapturingTransport(
        {
            "results": [
                {"id": "memory-1", "memory": {"content": long_text}, "score": 2.0},
                {
                    "chunk": {"content": "quiet arrival", "documentId": "document-2", "score": -1},
                },
                {"memory": "   "},
                {"unknown": "ignored"},
            ],
            "total": 4,
            "timing": 1,
            "ignored": "provider metadata",
        }
    )
    provider = SupermemoryMemoryProvider("value", SCOPE, transport)
    items = provider.retrieve("  prepare   arrival  ", SCOPE, MEMORY_LIMIT)

    assert transport.call == {
        "configured": True,
        "query": "prepare arrival",
        "scope": SCOPE,
        "limit": MEMORY_LIMIT,
    }
    assert len(items) == EXPECTED_ITEM_COUNT
    assert items[0].source_id == "memory-1"
    assert len(items[0].text) == MAX_MEMORY_TEXT_LENGTH
    assert items[0].relevance == 1.0
    assert items[1] == MemoryItem("document-2", "quiet arrival", 0.0)


def test_supermemory_handles_string_results_and_default_metadata() -> None:
    """String memory content receives safe default source and relevance values."""
    transport = CapturingTransport({"results": [{"memory": "preference"}]})
    items = SupermemoryMemoryProvider("value", SCOPE, transport).retrieve("goal", SCOPE, 1)
    assert items == (MemoryItem("supermemory-result", "preference", 0.0),)


def test_supermemory_handles_nested_metadata_misses_and_nonfinite_score() -> None:
    """Missing nested identifiers and nonfinite relevance safely use defaults."""
    transport = CapturingTransport(
        {
            "results": [
                {
                    "memory": {"content": "preference", "score": float("nan")},
                    "chunk": "unused fallback",
                }
            ]
        }
    )
    items = SupermemoryMemoryProvider("value", SCOPE, transport).retrieve("goal", SCOPE, 1)
    assert items == (MemoryItem("supermemory-result", "preference", 0.0),)


@pytest.mark.parametrize(
    ("api_key", "scope", "message"),
    [
        ("", SCOPE, "API key"),
        ("value", "browser supplied scope!", "bounded container tag"),
    ],
)
def test_supermemory_rejects_invalid_constructor_configuration(
    api_key: str,
    scope: str,
    message: str,
) -> None:
    """Credentials and scope must be explicit and fixed before retrieval."""
    with pytest.raises(ValueError, match=message):
        SupermemoryMemoryProvider(api_key, scope)


@pytest.mark.parametrize(
    ("query", "scope", "limit", "message"),
    [
        (" ", SCOPE, MEMORY_LIMIT, "cannot be blank"),
        ("x" * (MAX_QUERY_LENGTH + 1), SCOPE, MEMORY_LIMIT, "maximum length"),
        ("goal", "other-scope", MEMORY_LIMIT, "does not match"),
        ("goal", SCOPE, 0, "between one and five"),
        ("goal", SCOPE, 6, "between one and five"),
    ],
)
def test_supermemory_rejects_unbounded_search_inputs(
    query: str,
    scope: str,
    limit: int,
    message: str,
) -> None:
    """Browser-controlled scope and unbounded queries never reach transport."""
    transport = CapturingTransport({"results": []})
    provider = SupermemoryMemoryProvider("value", SCOPE, transport)
    with pytest.raises(ValueError, match=message):
        provider.retrieve(query, scope, limit)
    assert transport.call is None


def test_supermemory_rejects_malformed_response_envelope() -> None:
    """Provider schema drift fails closed rather than entering planner context."""
    provider = SupermemoryMemoryProvider("value", SCOPE, CapturingTransport({"results": "bad"}))
    with pytest.raises(ValidationError):
        provider.retrieve("goal", SCOPE, MEMORY_LIMIT)


def test_resilient_memory_reports_success_without_secret_material() -> None:
    """Successful retrieval exposes only safe provenance and bounded items."""
    provider = ResilientMemoryProvider(StaticMemory(), NoopMemoryProvider(), "supermemory")
    items = provider.retrieve("goal", SCOPE, MEMORY_LIMIT)
    assert items == (MemoryItem("source", "prefer economy", 0.9),)
    assert provider.last_report is not None
    assert not provider.last_report.used_fallback
    assert provider.last_report.failure_code is None


def test_resilient_memory_fails_closed_without_exception_text() -> None:
    """Provider failure yields empty context and a fixed non-disclosing code."""
    provider = ResilientMemoryProvider(FailingMemory(), NoopMemoryProvider(), "supermemory")
    before = provider.last_report
    assert before is None
    assert provider.retrieve("goal", SCOPE, MEMORY_LIMIT) == ()
    report = provider.last_report
    assert report is not None
    assert report.used_fallback
    assert report.failure_code == "memory_provider_unavailable"


def test_httpx_transport_uses_only_fixed_read_endpoint_and_bounded_payload() -> None:
    """The concrete transport has no configurable endpoint or write operation."""
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"results": []},
    )
    credential = "value"
    with patch("handsoff.adapters.memory.supermemory.httpx.post", return_value=response) as post:
        result = HttpxSupermemoryTransport().search(
            api_key=credential,
            query="goal",
            scope=SCOPE,
            limit=MEMORY_LIMIT,
        )
    assert result == {"results": []}
    assert post.call_args.args == (SUPERMEMORY_SEARCH_URL,)
    assert post.call_args.kwargs["json"] == {
        "q": "goal",
        "containerTag": SCOPE,
        "limit": MEMORY_LIMIT,
        "searchMode": "hybrid",
        "rerank": False,
        "aggregate": False,
        "rewriteQuery": False,
    }
    assert post.call_args.kwargs["timeout"] == HTTP_TIMEOUT_SECONDS
