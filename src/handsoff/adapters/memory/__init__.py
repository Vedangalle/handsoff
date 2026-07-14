"""Optional semantic-memory adapters."""

from handsoff.adapters.memory.fallback import MemoryRetrievalReport, ResilientMemoryProvider
from handsoff.adapters.memory.noop import NoopMemoryProvider
from handsoff.adapters.memory.supermemory import (
    HttpxSupermemoryTransport,
    SupermemoryMemoryProvider,
)

__all__ = [
    "HttpxSupermemoryTransport",
    "MemoryRetrievalReport",
    "NoopMemoryProvider",
    "ResilientMemoryProvider",
    "SupermemoryMemoryProvider",
]
