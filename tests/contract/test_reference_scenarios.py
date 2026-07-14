"""Contract tests for all committed deterministic scenario fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from handsoff.domain.capabilities import AutonomyMode, RiskClass
from handsoff.domain.execution import PlanState
from handsoff.domain.policies import PolicyDecision
from handsoff.domain.scenarios import ScenarioDefinition

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIRECTORY = ROOT / "scenarios"
EXPECTED_SCENARIOS = {
    "blocked_garage.yaml": (
        "scenario.blocked-garage",
        PolicyDecision.DENY,
        PlanState.REJECTED,
    ),
    "demand_response.yaml": (
        "scenario.demand-response",
        PolicyDecision.ALLOW,
        PlanState.SUCCEEDED,
    ),
    "false_proximity.yaml": (
        "scenario.false-proximity",
        PolicyDecision.DENY,
        PlanState.REJECTED,
    ),
    "nominal_arrival.yaml": (
        "scenario.nominal-arrival",
        PolicyDecision.ALLOW,
        PlanState.SUCCEEDED,
    ),
    "partial_failure.yaml": (
        "scenario.partial-failure",
        PolicyDecision.ALLOW,
        PlanState.PARTIALLY_SUCCEEDED,
    ),
    "stale_telemetry.yaml": (
        "scenario.stale-telemetry",
        PolicyDecision.DENY,
        PlanState.REJECTED,
    ),
}


def load_scenario(path: Path) -> ScenarioDefinition:
    """Load YAML through strict JSON-mode validation without coercing Python objects."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ScenarioDefinition.model_validate_json(json.dumps(raw))


def test_exact_reference_fixture_set_is_present() -> None:
    """Milestone 1 commits the six approved deterministic fixtures."""
    actual = {path.name for path in SCENARIO_DIRECTORY.glob("*.yaml")}
    assert actual == set(EXPECTED_SCENARIOS)


@pytest.mark.parametrize("filename", sorted(EXPECTED_SCENARIOS))
def test_reference_fixture_matches_contract_and_expected_result(filename: str) -> None:
    """Every reference fixture is strict, self-contained, and outcome-specific."""
    scenario = load_scenario(SCENARIO_DIRECTORY / filename)
    expected_id, expected_policy, expected_terminal = EXPECTED_SCENARIOS[filename]
    assert scenario.scenario_id == expected_id
    assert scenario.expected.policy_decision is expected_policy
    assert scenario.expected.terminal_plan_state is expected_terminal


@pytest.mark.parametrize("filename", sorted(EXPECTED_SCENARIOS))
def test_reference_fixture_round_trip_is_deterministic(filename: str) -> None:
    """Canonical JSON serialization can be parsed back without information loss."""
    scenario = load_scenario(SCENARIO_DIRECTORY / filename)
    serialized = scenario.model_dump_json()
    assert ScenarioDefinition.model_validate_json(serialized) == scenario


@pytest.mark.parametrize("filename", sorted(EXPECTED_SCENARIOS))
def test_reference_fixture_grants_no_live_or_r3_authority(filename: str) -> None:
    """Fixtures cannot declare live modes or prohibited R3 capabilities."""
    scenario = load_scenario(SCENARIO_DIRECTORY / filename)
    assert all(capability.risk_class is not RiskClass.R3 for capability in scenario.capabilities)
    assert all(
        capability.supported_modes <= {AutonomyMode.SIMULATION}
        for capability in scenario.capabilities
    )


def test_scenario_json_schema_forbids_unknown_fields() -> None:
    """Generated boundary schema advertises rejection of undeclared fields."""
    schema = ScenarioDefinition.model_json_schema()
    assert schema["additionalProperties"] is False
