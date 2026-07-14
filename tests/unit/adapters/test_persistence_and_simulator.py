"""Append-only persistence and deterministic simulator tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from handsoff.adapters.devices.simulator import ScriptedSimulatorAdapter
from handsoff.adapters.persistence.memory import InMemoryLedger
from handsoff.adapters.persistence.sqlite import SQLiteLedger
from handsoff.domain.events import EventKind, LedgerEvent
from handsoff.domain.scenarios import ScriptedCapabilityOutcome, ScriptedResult
from handsoff.ports.capability_adapter import DispatchStatus
from handsoff.ports.repositories import LedgerRepository
from tests.fixtures.contracts import NOW, make_action, make_capability, make_goal, make_observation

if TYPE_CHECKING:
    from pathlib import Path


def make_event(sequence: int = 1, event_id: str = "event.plan-arrival.1") -> LedgerEvent:
    """Build one valid goal event."""
    return LedgerEvent(
        event_id=event_id,
        stream_id="plan.arrival",
        sequence_number=sequence,
        kind=EventKind.GOAL_RECEIVED,
        occurred_at=NOW,
        correlation_id="correlation.plan-arrival",
        payload=make_goal(),
    )


def test_in_memory_ledger_enforces_event_and_sequence_identity() -> None:
    """Streams accept only the next unique immutable event."""
    ledger = InMemoryLedger()
    assert isinstance(ledger, LedgerRepository)
    first = make_event()
    ledger.append(first)
    assert ledger.list_stream("plan.arrival") == (first,)
    assert ledger.list_stream("plan.missing") == ()
    with pytest.raises(ValueError, match="identifier"):
        ledger.append(first)
    with pytest.raises(ValueError, match="sequence"):
        ledger.append(make_event(sequence=3, event_id="event.plan-arrival.3"))


def test_sqlite_ledger_round_trips_and_rejects_duplicate_identity(tmp_path: Path) -> None:
    """SQLite persistence revalidates JSON and preserves event order."""
    ledger = SQLiteLedger(f"sqlite+pysqlite:///{tmp_path / 'ledger.sqlite3'}")
    event = make_event()
    ledger.append(event)
    assert ledger.list_stream("plan.arrival") == (event,)
    assert ledger.list_stream("plan.missing") == ()
    with pytest.raises(ValueError, match="already exists"):
        ledger.append(event)
    ledger.close()


def test_simulator_returns_scripted_effect_and_suppresses_duplicate() -> None:
    """One idempotency key can apply at most one simulated effect."""
    outcome = ScriptedCapabilityOutcome(
        capability_id="device.prepare",
        attempt=1,
        result=ScriptedResult.EFFECT_OBSERVED,
        effect_observations=(make_observation(value="ready"),),
    )
    adapter = ScriptedSimulatorAdapter((outcome,))
    action = make_action()
    capability = make_capability()
    first = adapter.dispatch(action, capability, 1)
    duplicate = adapter.dispatch(action, capability, 1)
    assert first.status is DispatchStatus.EFFECT_OBSERVED
    assert first.observations
    assert duplicate.duplicate
    assert duplicate.observations == ()


def test_simulator_returns_failure_when_attempt_is_unscripted() -> None:
    """Missing fixture behavior fails closed."""
    result = ScriptedSimulatorAdapter(()).dispatch(make_action(), make_capability(), 1)
    assert result.status is DispatchStatus.FAILED


def test_simulator_maps_timed_out_result() -> None:
    """Script status maps exactly to the adapter port."""
    outcome = ScriptedCapabilityOutcome(
        capability_id="device.prepare",
        attempt=1,
        result=ScriptedResult.TIMED_OUT,
    )
    result = ScriptedSimulatorAdapter((outcome,)).dispatch(
        make_action(),
        make_capability(),
        1,
    )
    assert result.status is DispatchStatus.TIMED_OUT


def test_simulator_rejects_action_contract_mismatch() -> None:
    """An adapter never dispatches a different capability contract."""
    with pytest.raises(ValueError, match="do not match"):
        ScriptedSimulatorAdapter(()).dispatch(
            make_action(),
            make_capability(capability_id="other.prepare"),
            1,
        )
