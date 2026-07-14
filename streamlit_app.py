"""Handsoff Milestone 4 Streamlit operator demonstration."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import streamlit as st

from handsoff.domain.events import EventKind
from handsoff.presentation import DemoFacade, DemoMode, DemoRun, DemoSession, DemoSettings

ROOT = Path(__file__).resolve().parent
SESSION_KEY = "handsoff_demo_session"


def _server_settings() -> DemoSettings:
    """Read allowlisted server-side secrets without displaying or logging values."""
    try:
        values = st.secrets.to_dict()
    except Exception:  # noqa: BLE001 - absent Streamlit secret storage is a valid offline mode
        values = {}
    return DemoSettings.from_mapping(values)


def _new_session() -> DemoSession:
    """Construct one session-owned facade and no shared mutable runtime state."""
    return DemoSession(DemoFacade(_server_settings(), ROOT / "scenarios"))


def _session() -> DemoSession:
    """Return the current browser's isolated demonstration session."""
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = _new_session()
    return cast("DemoSession", st.session_state[SESSION_KEY])


def _render_header() -> None:
    """Render the product framing and immutable prototype boundary."""
    st.title("Handsoff")
    st.markdown("### Goals in. Policy checked. Outcomes verified.")
    st.caption(
        "A local-first simulation runtime where AI may propose a typed plan, "
        "but deterministic policy alone controls authority."
    )
    st.warning(
        "Simulation only — no real devices, Home Assistant writes, or R3 actions are available."
    )


def _render_sidebar(session: DemoSession) -> tuple[str, DemoMode]:
    """Render only committed scenarios and fixed provider modes."""
    settings = session.facade.settings
    options = session.facade.scenarios()
    by_id = {option.scenario_id: option for option in options}

    st.sidebar.header("Demonstration control")
    scenario_id = st.sidebar.selectbox(
        "Reference scenario",
        options=tuple(by_id),
        format_func=lambda value: by_id[value].title,
        key="scenario_id",
    )
    mode = st.sidebar.selectbox(
        "Planning mode",
        options=tuple(DemoMode),
        format_func=lambda value: value.label,
        key="demo_mode",
    )
    st.sidebar.caption(by_id[scenario_id].description)
    st.sidebar.divider()
    st.sidebar.markdown("**Provider readiness**")
    st.sidebar.write(f"Gemini: {'configured' if settings.gemini_available else 'offline fallback'}")
    st.sidebar.write(
        "Supermemory: "
        f"{'configured read-only' if settings.supermemory_available else 'empty-context fallback'}"
    )
    st.sidebar.caption("Credentials and provider responses are never displayed.")

    run_clicked = st.sidebar.button("Run policy-bounded simulation", type="primary")
    reset_clicked = st.sidebar.button("Reset session")
    if reset_clicked:
        session.reset()
        st.rerun()
    if run_clicked:
        session.run(scenario_id, mode)
    return scenario_id, mode


def _render_summary(run: DemoRun) -> None:
    """Render result metrics from a typed DemoRun without computing policy."""
    runtime = run.assessment.runtime
    if run.assessment.matched:
        st.success("Observed runtime evidence matches the committed scenario vector.")
    else:
        st.error("Observed runtime evidence differs from the committed scenario vector.")
    columns = st.columns(4)
    columns[0].metric("Policy", runtime.policy.decision.value.replace("_", " ").title())
    columns[1].metric("Terminal state", runtime.terminal_plan_state.value.replace("_", " ").title())
    columns[2].metric("Ledger events", len(runtime.events))
    columns[3].metric("Verified goals", sum(item.satisfied for item in runtime.verifications))

    planner = runtime.planner
    st.caption(
        f"Planner: {planner.provider} / {planner.model} · "
        f"fallback: {'yes' if planner.used_fallback else 'no'} · "
        f"trusted-input fingerprint: {run.trusted_input_fingerprint}"
    )
    if planner.used_fallback:
        st.info("Gemini was unavailable or invalid; deterministic planning completed offline.")
    if run.memory.used_fallback:
        st.info("Supermemory was unavailable or invalid; planning continued with empty context.")


def _render_world(run: DemoRun) -> None:
    """Render initial and effect observations carried by ledger evidence."""
    observations = [
        event.payload.model_dump(mode="json")
        for event in run.assessment.runtime.events
        if event.kind is EventKind.OBSERVATION_RECORDED
    ]
    st.subheader("Timestamped world evidence")
    st.dataframe(observations, width="stretch", hide_index=True)


def _render_plan(run: DemoRun) -> None:
    """Render the untrusted proposal and declared action contracts."""
    plan = run.assessment.runtime.planner.plan
    st.subheader("Untrusted typed proposal")
    st.caption("A schema-valid proposal is still not authorization.")
    st.dataframe(
        [
            {
                "action": action.action_id,
                "capability": action.capability_id,
                "version": action.capability_version,
                "target": action.target_entity_id,
                "dependencies": ", ".join(action.depends_on) or "—",
                "failure strategy": action.on_failure.value,
            }
            for action in plan.actions
        ],
        width="stretch",
        hide_index=True,
    )
    with st.expander("Inspect complete proposal contract"):
        st.json(plan.model_dump(mode="json"), expanded=False)


def _render_policy(run: DemoRun) -> None:
    """Render deterministic plan and action policy decisions."""
    policy = run.assessment.runtime.policy
    st.subheader("Deterministic authority boundary")
    st.write("Plan decision:", policy.decision.value)
    st.write("Reasons:", "; ".join(policy.reasons))
    st.dataframe(
        [
            {
                "action": decision.action_id,
                "risk": decision.risk_class.value,
                "decision": decision.decision.value,
                "reasons": "; ".join(decision.reasons),
            }
            for decision in policy.action_decisions
        ],
        width="stretch",
        hide_index=True,
    )
    st.caption("Approval requirements are explicit; this public simulation cannot bypass them.")


def _render_execution(run: DemoRun) -> None:
    """Render plan and action state transitions without issuing commands."""
    runtime = run.assessment.runtime
    st.subheader("Execution state machine")
    st.markdown("**Plan transitions**")
    st.dataframe(
        [transition.model_dump(mode="json") for transition in runtime.plan_transitions],
        width="stretch",
        hide_index=True,
    )
    st.markdown("**Action transitions**")
    st.dataframe(
        [transition.model_dump(mode="json") for transition in runtime.action_transitions],
        width="stretch",
        hide_index=True,
    )


def _render_verification(run: DemoRun) -> None:
    """Render independent condition evidence after simulated dispatch."""
    st.subheader("Outcome verification")
    st.caption("Adapter acceptance alone never counts as physical-effect evidence.")
    st.dataframe(
        [item.model_dump(mode="json") for item in run.assessment.runtime.verifications],
        width="stretch",
        hide_index=True,
    )


def _render_ledger(run: DemoRun) -> None:
    """Render the ordered evidence stream without raw provider material."""
    st.subheader("Append-only evidence ledger")
    st.dataframe(
        [
            {
                "sequence": event.sequence_number,
                "kind": event.kind.value,
                "occurred at": event.occurred_at.isoformat(),
                "subject": event.payload.__class__.__name__,
                "event": event.event_id,
            }
            for event in run.assessment.runtime.events
        ],
        width="stretch",
        hide_index=True,
    )


def _render_memory(run: DemoRun) -> None:
    """Render bounded memory context and its non-authoritative trust status."""
    memory = run.memory
    st.subheader("Supermemory context boundary")
    st.write(
        {
            "provider": memory.provider,
            "scope": memory.scope,
            "read only": True,
            "fallback": memory.used_fallback,
            "items": len(memory.items),
        }
    )
    if memory.items:
        st.dataframe(
            [
                {
                    "source": item.source_id,
                    "relevance": item.relevance,
                    "untrusted context": item.text,
                }
                for item in memory.items
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("No external context was supplied to this proposal.")
    st.markdown(
        "Memory can influence only planner preference context. It cannot add capabilities, "
        "change risk, grant approval, dispatch actions, or satisfy verification."
    )
    st.code(f"trusted inputs: {run.trusted_input_fingerprint}", language="text")


def main() -> None:
    """Render the complete Milestone 4 public operator surface."""
    st.set_page_config(page_title="Handsoff", page_icon="◼", layout="wide")
    _render_header()
    session = _session()
    _render_sidebar(session)
    run = session.last_run
    if run is None:
        st.info("Select a reference scenario and run the policy-bounded simulation.")
        st.markdown(
            "The deterministic baseline requires no network or credential. Optional providers "
            "degrade to the same offline runtime without weakening policy."
        )
        return

    _render_summary(run)
    tabs = st.tabs(
        ["World", "Proposal", "Policy", "Execution", "Verification", "Ledger", "Memory & trust"]
    )
    renderers = (
        _render_world,
        _render_plan,
        _render_policy,
        _render_execution,
        _render_verification,
        _render_ledger,
        _render_memory,
    )
    for tab, renderer in zip(tabs, renderers, strict=True):
        with tab:
            renderer(run)


if __name__ == "__main__":
    main()
