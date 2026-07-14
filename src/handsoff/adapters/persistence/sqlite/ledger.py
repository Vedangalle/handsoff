"""Transactional SQLite append-only operational ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.exc import IntegrityError

from handsoff.domain.events import LedgerEvent

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

_METADATA = MetaData()
_EVENTS = Table(
    "ledger_events",
    _METADATA,
    Column("event_id", String(128), primary_key=True),
    Column("stream_id", String(128), nullable=False),
    Column("sequence_number", Integer, nullable=False),
    Column("event_json", Text, nullable=False),
    UniqueConstraint("stream_id", "sequence_number", name="uq_ledger_stream_sequence"),
)


class SQLiteLedger:
    """Persist event envelopes as canonical validated JSON."""

    def __init__(self, url: str = "sqlite+pysqlite:///:memory:") -> None:
        """Create the ledger schema at the supplied SQLite URL."""
        self._engine: Engine = create_engine(url)
        _METADATA.create_all(self._engine)

    def append(self, event: LedgerEvent) -> None:
        """Atomically append one immutable event."""
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    _EVENTS.insert().values(
                        event_id=event.event_id,
                        stream_id=event.stream_id,
                        sequence_number=event.sequence_number,
                        event_json=event.model_dump_json(),
                    )
                )
        except IntegrityError as error:
            message = "ledger event identifier or stream sequence already exists"
            raise ValueError(message) from error

    def list_stream(self, stream_id: str) -> tuple[LedgerEvent, ...]:
        """Read and revalidate one stream in sequence order."""
        statement = (
            _EVENTS.select()
            .where(_EVENTS.c.stream_id == stream_id)
            .order_by(_EVENTS.c.sequence_number)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(LedgerEvent.model_validate_json(row["event_json"]) for row in rows)

    def close(self) -> None:
        """Release pooled SQLite connections."""
        self._engine.dispose()


__all__ = ["SQLiteLedger"]
