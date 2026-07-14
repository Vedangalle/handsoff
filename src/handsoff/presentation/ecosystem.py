"""Typed whole-home projection derived from scenario and runtime evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, cast

from handsoff.domain.events import EventKind
from handsoff.domain.execution import ActionState
from handsoff.domain.policies import PolicyDecision

if TYPE_CHECKING:
    from pydantic import JsonValue

    from handsoff.application.execute_plan import RuntimeResult
    from handsoff.domain.observations import Observation
    from handsoff.domain.scenarios import ScenarioDefinition


class EcosystemStatus(StrEnum):
    """Presentation-only state derived from authoritative runtime evidence."""

    IDLE = "idle"
    READY = "ready"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    FAILED = "failed"
    PROHIBITED = "prohibited"


@dataclass(frozen=True, slots=True)
class EcosystemDevice:
    """One inspectable room or device in the whole-home projection."""

    device_id: str
    label: str
    room: str
    capability_ids: tuple[str, ...]
    status: EcosystemStatus
    value: str
    detail: str


@dataclass(frozen=True, slots=True)
class EcosystemView:
    """Complete spatial projection consumed by the Streamlit adapter."""

    scenario_id: str
    mission_state: str
    devices: tuple[EcosystemDevice, ...]

    def device(self, device_id: str) -> EcosystemDevice:
        """Return one fixed ecosystem device by identifier."""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        message = "ecosystem device is not declared"
        raise KeyError(message)


@dataclass(frozen=True, slots=True)
class _DeviceSpec:
    device_id: str
    label: str
    room: str
    capability_ids: tuple[str, ...]
    entity_id: str
    property_id: str
    detail: str


@dataclass(frozen=True, slots=True)
class _ProjectionContext:
    scenario_id: str
    observations: dict[tuple[str, str], Observation]
    declared: set[str]
    decisions: dict[str, PolicyDecision]
    final_states: dict[str, ActionState]


_DEVICE_SPECS = (
    _DeviceSpec(
        "vehicle",
        "Arrival signal",
        "Driveway",
        (),
        "vehicle.primary",
        "destination_confidence",
        "Fresh vehicle proximity evidence",
    ),
    _DeviceSpec(
        "garage",
        "Garage",
        "Garage",
        ("garage.open",),
        "garage.main",
        "door_state",
        "Bounded entry preparation",
    ),
    _DeviceSpec(
        "charger",
        "EV charger",
        "Garage",
        ("charger.prepare",),
        "charger.home",
        "readiness",
        "Prepared without energizing",
    ),
    _DeviceSpec(
        "climate",
        "Climate",
        "Living room",
        ("climate.set-target", "climate.set-economy"),
        "room.living",
        "temperature_setpoint",
        "Comfort within energy policy",
    ),
    _DeviceSpec(
        "lighting",
        "Welcome lights",
        "Living room",
        ("lighting.set-welcome",),
        "lighting.living",
        "scene",
        "Coordinated arrival scene",
    ),
    _DeviceSpec(
        "fan",
        "Ceiling fan",
        "Living room",
        ("fan.set-comfort",),
        "fan.living",
        "speed",
        "Preferred low-speed airflow",
    ),
    _DeviceSpec(
        "media",
        "Living-room TV",
        "Living room",
        ("media.resume-usual", "media.prepare"),
        "media.living",
        "playback_state",
        "Usual program from bounded preference context",
    ),
    _DeviceSpec(
        "coffee",
        "Coffee maker",
        "Kitchen",
        ("coffee.brew-arrival",),
        "coffee.kitchen",
        "brew_state",
        "Guarded by water, cup, and arrival evidence",
    ),
    _DeviceSpec(
        "ice",
        "Ice maker",
        "Kitchen",
        ("ice.prepare",),
        "ice-maker.kitchen",
        "production_state",
        "Arrival-ready kitchen preparation",
    ),
    _DeviceSpec(
        "grid",
        "Energy signal",
        "Utility",
        (),
        "grid.home",
        "demand_response_active",
        "Grid constraint remains authoritative",
    ),
)


def build_ecosystem_view(
    scenario: ScenarioDefinition,
    runtime: RuntimeResult | None = None,
) -> EcosystemView:
    """Project typed observations and decisions into a fixed spatial device set."""
    observations = _latest_observations(scenario, runtime)
    declared = {capability.capability_id for capability in scenario.capabilities}
    decisions, final_states = _runtime_states(runtime)
    context = _ProjectionContext(
        scenario.scenario_id,
        observations,
        declared,
        decisions,
        final_states,
    )
    devices = tuple(_project_device(spec, context) for spec in _DEVICE_SPECS)
    fireplace = EcosystemDevice(
        device_id="fireplace",
        label="Fireplace",
        room="Living room",
        capability_ids=(),
        status=EcosystemStatus.PROHIBITED,
        value="R3 locked",
        detail="Fire and gas ignition are never exposed by this prototype",
    )
    mission_state = runtime.terminal_plan_state.value if runtime is not None else "staged"
    return EcosystemView(scenario.scenario_id, mission_state, (*devices, fireplace))


def _latest_observations(
    scenario: ScenarioDefinition,
    runtime: RuntimeResult | None,
) -> dict[tuple[str, str], Observation]:
    observations = list(scenario.initial_observations)
    if runtime is not None:
        observations = [
            cast("Observation", event.payload)
            for event in runtime.events
            if event.kind is EventKind.OBSERVATION_RECORDED
        ]
    ordered = sorted(observations, key=lambda item: (item.observed_at, item.observation_id))
    return {(item.entity_id, item.property_id): item for item in ordered}


def _runtime_states(
    runtime: RuntimeResult | None,
) -> tuple[dict[str, PolicyDecision], dict[str, ActionState]]:
    if runtime is None:
        return {}, {}
    actions = {action.action_id: action.capability_id for action in runtime.planner.plan.actions}
    decisions = {
        actions[result.action_id]: result.decision for result in runtime.policy.action_decisions
    }
    final_states: dict[str, ActionState] = {}
    for transition in runtime.action_transitions:
        final_states[actions[transition.action_id]] = transition.to_state
    return decisions, final_states


def _project_device(
    spec: _DeviceSpec,
    context: _ProjectionContext,
) -> EcosystemDevice:
    capability = next((item for item in spec.capability_ids if item in context.declared), None)
    observation = context.observations.get((spec.entity_id, spec.property_id))
    status = _status(capability, spec.device_id, observation, context)
    value = _display_value(spec.device_id, observation, context.observations)
    if capability is not None and observation is None:
        value = {
            EcosystemStatus.BLOCKED: "Withheld by policy",
            EcosystemStatus.FAILED: "No effect observed",
        }.get(status, "Awaiting evidence")
    return EcosystemDevice(
        spec.device_id,
        spec.label,
        spec.room,
        spec.capability_ids,
        status,
        value,
        spec.detail,
    )


def _status(
    capability: str | None,
    device_id: str,
    observation: Observation | None,
    context: _ProjectionContext,
) -> EcosystemStatus:
    status = EcosystemStatus.IDLE
    if device_id == "vehicle" and observation is not None:
        status = (
            EcosystemStatus.BLOCKED
            if context.scenario_id in {"scenario.false-proximity", "scenario.stale-telemetry"}
            else EcosystemStatus.READY
        )
    elif device_id == "grid" and observation is not None:
        status = EcosystemStatus.READY
    elif capability is not None:
        status = EcosystemStatus.READY
        if context.decisions.get(capability) is PolicyDecision.DENY:
            status = EcosystemStatus.BLOCKED
        final = context.final_states.get(capability)
        if final is ActionState.VERIFIED:
            status = EcosystemStatus.VERIFIED
        elif final in {ActionState.FAILED, ActionState.TIMED_OUT}:
            status = EcosystemStatus.FAILED
    return status


def _display_value(
    device_id: str,
    observation: Observation | None,
    observations: dict[tuple[str, str], Observation],
) -> str:
    if device_id == "media":
        program = observations.get(("media.living", "program"))
        if program is not None and str(program.value) != "none":
            return f"{program.value} · {observation.value if observation else 'idle'}"
    if observation is None:
        return "Not in this mission"
    return _format_value(observation.value, observation.unit)


def _format_value(value: JsonValue, unit: str | None) -> str:
    if type(value) is bool:
        return "Active" if value else "Inactive"
    if unit == "degrees_celsius":
        return f"{value} °C"
    if unit == "ratio" and isinstance(value, (int, float)):
        return f"{float(value) * 100:.0f}% confidence"
    return str(value).replace("_", " ").title()


__all__ = ["EcosystemDevice", "EcosystemStatus", "EcosystemView", "build_ecosystem_view"]
