"""Evidence-driven whole-home presentation projection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from handsoff.presentation import (
    DemoFacade,
    DemoMode,
    DemoSettings,
    EcosystemStatus,
    build_ecosystem_view,
)
from handsoff.presentation.ecosystem import _format_value

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "scenarios"


def test_staged_projection_declares_devices_without_claiming_execution() -> None:
    """A selected mission shows scope while preserving staged truth."""
    facade = DemoFacade(DemoSettings(), SCENARIOS)
    view = build_ecosystem_view(facade.scenario("scenario.nominal-arrival"))

    assert view.mission_state == "staged"
    assert view.device("vehicle").status is EcosystemStatus.READY
    assert view.device("garage").status is EcosystemStatus.READY
    assert view.device("garage").value == "Closed"
    assert view.device("media").value == "Idle"
    assert view.device("grid").status is EcosystemStatus.IDLE
    assert view.device("grid").value == "Not in this mission"
    assert view.device("fireplace").status is EcosystemStatus.PROHIBITED
    assert view.device("fireplace").value == "R3 locked"
    with pytest.raises(KeyError, match="not declared"):
        view.device("browser-invented-device")


def test_nominal_runtime_projects_all_bounded_homecoming_effects() -> None:
    """The house activates only from independently observed runtime effects."""
    facade = DemoFacade(DemoSettings(), SCENARIOS)
    run = facade.run("scenario.nominal-arrival", DemoMode.SYNTHETIC_MEMORY)
    view = build_ecosystem_view(run.scenario, run.assessment.runtime)

    assert view.mission_state == "succeeded"
    for device_id in (
        "garage",
        "charger",
        "climate",
        "lighting",
        "fan",
        "media",
        "coffee",
        "ice",
    ):
        assert view.device(device_id).status is EcosystemStatus.VERIFIED
    assert view.device("vehicle").value == "99% confidence"
    assert view.device("climate").value == "22.0 °C"
    assert view.device("media").value == "Orbit Seven · playing"
    assert view.device("coffee").value == "Ready"
    assert view.device("ice").value == "Making"


@pytest.mark.parametrize(
    "scenario_id",
    ["scenario.false-proximity", "scenario.stale-telemetry"],
)
def test_untrusted_arrival_evidence_is_spatially_marked_blocked(scenario_id: str) -> None:
    """False or stale proximity never appears as a trusted green signal."""
    facade = DemoFacade(DemoSettings(), SCENARIOS)
    run = facade.run(scenario_id, DemoMode.DETERMINISTIC)
    view = build_ecosystem_view(run.scenario, run.assessment.runtime)

    assert view.device("vehicle").status is EcosystemStatus.BLOCKED
    assert view.device("garage").status is EcosystemStatus.BLOCKED


def test_policy_failure_and_partial_execution_remain_visually_distinct() -> None:
    """A denied action is blocked while a dispatched failure is failed."""
    facade = DemoFacade(DemoSettings(), SCENARIOS)

    denied = facade.run("scenario.blocked-garage", DemoMode.DETERMINISTIC)
    denied_view = build_ecosystem_view(denied.scenario, denied.assessment.runtime)
    assert denied_view.device("garage").status is EcosystemStatus.BLOCKED
    assert denied_view.device("garage").value == "Withheld by policy"
    assert denied_view.device("vehicle").status is EcosystemStatus.READY

    partial = facade.run("scenario.partial-failure", DemoMode.DETERMINISTIC)
    partial_view = build_ecosystem_view(partial.scenario, partial.assessment.runtime)
    assert partial_view.device("charger").status is EcosystemStatus.VERIFIED
    assert partial_view.device("media").status is EcosystemStatus.FAILED
    assert partial_view.device("media").value == "No effect observed"


def test_energy_constraint_is_visible_without_becoming_device_authority() -> None:
    """Grid evidence is ready while the bounded climate action is verified."""
    facade = DemoFacade(DemoSettings(), SCENARIOS)
    run = facade.run("scenario.demand-response", DemoMode.DETERMINISTIC)
    view = build_ecosystem_view(run.scenario, run.assessment.runtime)

    assert view.device("grid").status is EcosystemStatus.READY
    assert view.device("grid").value == "Active"
    assert view.device("climate").status is EcosystemStatus.VERIFIED
    assert view.device("climate").value == "25.0 °C"


def test_value_formatting_is_total_for_bounded_json_values() -> None:
    """Unexpected provider-shaped values degrade to text, never fake telemetry."""
    assert _format_value(value=False, unit=None) == "Inactive"
    assert _format_value("unknown", "ratio") == "Unknown"
    assert _format_value("stand_by", None) == "Stand By"
