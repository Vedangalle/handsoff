"""Execute every committed scenario through the deterministic runtime."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from handsoff.adapters.persistence.sqlite import SQLiteLedger
from handsoff.application.run_scenario import ScenarioRunner, load_scenario
from handsoff.domain.execution import PlanState
from handsoff.domain.policies import PolicyDecision

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = tuple(sorted((ROOT / "scenarios").glob("*.yaml")))
MISMATCH_CATEGORY_COUNT = 6


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda path: path.stem)
def test_reference_scenario_matches_every_expected_result(path: Path) -> None:
    """Policy, dispatch, terminal state, and verification match the test vector."""
    assessment = ScenarioRunner().run(load_scenario(path))
    assert assessment.matched, assessment.mismatches
    assert assessment.runtime.events
    assert [event.sequence_number for event in assessment.runtime.events] == list(
        range(1, len(assessment.runtime.events) + 1)
    )


def test_scenario_comparison_reports_every_mismatch_category() -> None:
    """Acceptance diagnostics identify each observable contract difference."""
    scenario = load_scenario(ROOT / "scenarios" / "nominal_arrival.yaml")
    runtime = ScenarioRunner().run(scenario).runtime
    wrong = replace(
        runtime,
        policy=runtime.policy.model_copy(update={"decision": PolicyDecision.DENY}),
        terminal_plan_state=PlanState.FAILED,
        dispatched_capability_ids=(),
        withheld_capability_ids=("garage.open",),
        verifications=tuple(
            result.model_copy(update={"satisfied": False}) for result in runtime.verifications
        ),
    )
    mismatches = ScenarioRunner.compare(scenario, wrong)
    assert len(mismatches) == MISMATCH_CATEGORY_COUNT


def test_nominal_runtime_replays_all_event_payloads_from_sqlite(tmp_path: Path) -> None:
    """Persistent replay preserves the complete heterogeneous evidence stream."""
    scenario = load_scenario(ROOT / "scenarios" / "nominal_arrival.yaml")
    ledger = SQLiteLedger(f"sqlite+pysqlite:///{tmp_path / 'runtime.sqlite3'}")
    runtime = ScenarioRunner(ledger=ledger).run(scenario).runtime
    assert ledger.list_stream(runtime.planner.plan.plan_id) == runtime.events
    ledger.close()
