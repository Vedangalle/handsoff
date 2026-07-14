"""Handsoff Streamlit mission-control demonstration."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, cast

import streamlit as st

from handsoff.domain.events import EventKind
from handsoff.presentation import DemoFacade, DemoMode, DemoRun, DemoSession, DemoSettings

if TYPE_CHECKING:
    from handsoff.domain.scenarios import ScenarioDefinition

ROOT = Path(__file__).resolve().parent
SESSION_KEY = "handsoff_demo_session"


def _server_settings() -> DemoSettings:
    """Read allowlisted server-side secrets without displaying or logging values."""
    try:
        values = st.secrets.to_dict()
    except Exception:  # noqa: BLE001 - absent secret storage is a valid offline mode
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


def _humanize(value: str) -> str:
    """Convert a machine identifier into compact display text."""
    return value.replace("_", " ").replace("-", " ").title()


def _inject_design_system() -> None:
    """Install the original Handsoff visual system without remote assets."""
    st.markdown(
        """
        <style>
        :root {
            --ho-panel-solid: #ffffff;
            --ho-line: rgba(27, 70, 135, .13);
            --ho-line-strong: rgba(27, 70, 135, .24);
            --ho-text: #0c1830;
            --ho-muted: #617087;
            --ho-blue: #2368e8;
            --ho-blue-bright: #4387ff;
            --ho-green: #20b26b;
            --ho-amber: #cf8614;
            --ho-red: #d84d5b;
        }

        .stApp {
            background:
                radial-gradient(circle at 76% 0%, rgba(72, 134, 255, .16), transparent 34rem),
                radial-gradient(circle at 12% 42%, rgba(153, 191, 255, .12), transparent 27rem),
                linear-gradient(180deg, #f8faff 0%, #f2f6fc 58%, #edf3fb 100%);
            color: var(--ho-text);
        }

        [data-testid="stAppViewContainer"] > .main { background: transparent; }
        [data-testid="stHeader"] { background: rgba(248, 250, 255, .78); }
        [data-testid="stToolbar"] { opacity: .55; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1420px;
            padding: 3.1rem 3.2rem 6rem;
        }

        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 10% 12%, rgba(62, 127, 245, .24), transparent 15rem),
                linear-gradient(180deg, #102447 0%, #0b1931 100%);
            border-right: 1px solid rgba(255, 255, 255, .08);
        }
        [data-testid="stSidebarContent"] { padding: 1.25rem .7rem 2rem; }
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] strong { color: #f6f9ff; }
        [data-testid="stSidebar"] .ho-kicker { color: #94baff; }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #afbdd3; }
        [data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, .12); }

        h1, h2, h3 { letter-spacing: -.035em; }
        h1 {
            font-size: clamp(3.7rem, 7vw, 7.2rem) !important;
            line-height: .9 !important;
            margin: .25rem 0 .65rem !important;
            font-weight: 650 !important;
            background: linear-gradient(105deg, #0b1830 22%, #205fcf 68%, #4d8eff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        h2 { font-size: clamp(1.65rem, 3vw, 2.45rem) !important; }
        h3 { font-size: 1.1rem !important; }
        p, label, [data-testid="stCaptionContainer"] { letter-spacing: -.005em; }

        .ho-kicker {
            display: flex;
            align-items: center;
            gap: .55rem;
            color: var(--ho-blue);
            font: 700 .71rem/1.1 ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .16em;
            text-transform: uppercase;
            margin-bottom: 1.1rem;
        }
        .ho-kicker::before {
            content: "";
            width: .48rem;
            height: .48rem;
            border-radius: 50%;
            background: var(--ho-green);
            box-shadow: 0 0 16px rgba(32, 178, 107, .62);
            animation: ho-pulse 2.8s ease-in-out infinite;
        }
        .ho-deck {
            max-width: 820px;
            color: #4c5e77;
            font-size: clamp(1.12rem, 2vw, 1.45rem);
            line-height: 1.55;
            margin: 0 0 1.55rem;
        }
        .ho-deck strong { color: var(--ho-text); font-weight: 600; }
        .ho-rule { border-top: 1px solid var(--ho-line); margin: 2.2rem 0; }

        .ho-badge-row { display: flex; flex-wrap: wrap; gap: .55rem; margin: 1.2rem 0 2.3rem; }
        .ho-badge {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border: 1px solid var(--ho-line-strong);
            border-radius: 999px;
            padding: .52rem .78rem;
            color: #4e617b;
            background: rgba(255, 255, 255, .68);
            font: 650 .68rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .06em;
            text-transform: uppercase;
        }
        .ho-badge--live { color: #147d4d; border-color: rgba(32, 178, 107, .34); }
        .ho-dot { width: .38rem; height: .38rem; border-radius: 50%; background: currentColor; }

        .ho-notice {
            display: flex;
            gap: .8rem;
            align-items: center;
            border: 1px solid rgba(207, 134, 20, .28);
            background: rgba(255, 246, 225, .78);
            padding: .9rem 1rem;
            color: #76511b;
            font-size: .84rem;
            margin: 1rem 0 2rem;
            border-radius: 12px;
        }
        .ho-notice b { color: var(--ho-amber); font-family: ui-monospace, monospace; }

        .ho-section-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--ho-line);
            padding: .9rem 0 1.4rem;
            margin-top: 2.3rem;
            color: var(--ho-muted);
            font: 700 .68rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .15em;
            text-transform: uppercase;
        }
        .ho-section-label span:last-child { color: #8a99ae; }

        .ho-grid { display: grid; gap: .85rem; }
        .ho-grid--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .ho-grid--4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .ho-card {
            position: relative;
            min-height: 150px;
            border: 1px solid var(--ho-line);
            background: linear-gradient(145deg, rgba(255, 255, 255, .96), rgba(242, 247, 255, .9));
            box-shadow: 0 10px 30px rgba(40, 72, 125, .045);
            padding: 1.2rem;
            overflow: hidden;
            border-radius: 14px;
        }
        .ho-card::after {
            content: "";
            position: absolute;
            inset: auto -25% -80% 20%;
            height: 130px;
            background: radial-gradient(ellipse, rgba(67, 135, 255, .1), transparent 67%);
            pointer-events: none;
        }
        .ho-card:hover { border-color: var(--ho-line-strong); transform: translateY(-1px); }
        .ho-card-num { color: var(--ho-blue); font: 700 .67rem/1 ui-monospace, monospace; }
        .ho-card h3 { color: var(--ho-text); margin: 1.2rem 0 .5rem; }
        .ho-card p { color: var(--ho-muted); font-size: .82rem; line-height: 1.5; margin: 0; }

        .ho-hero-panel {
            border: 1px solid var(--ho-line);
            background:
                linear-gradient(115deg, rgba(255, 255, 255, .98), rgba(232, 241, 255, .9)),
                repeating-linear-gradient(90deg, transparent, transparent 49px, rgba(35,104,232,.04) 50px);
            box-shadow: 0 18px 52px rgba(36, 88, 168, .08);
            padding: clamp(1.3rem, 3vw, 2.25rem);
            margin: 1.25rem 0 1rem;
            border-radius: 18px;
        }
        .ho-hero-top { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
        .ho-result {
            color: var(--ho-text);
            font-size: clamp(2.25rem, 5vw, 4.8rem);
            line-height: 1;
            letter-spacing: -.06em;
            margin: .65rem 0 1rem;
        }
        .ho-result--allow { color: #158456; }
        .ho-result--deny { color: var(--ho-red); }
        .ho-caption { color: var(--ho-muted); font-size: .8rem; line-height: 1.5; }

        .ho-pipeline { display: grid; grid-template-columns: repeat(6, 1fr); margin: 1.25rem 0 2rem; }
        .ho-stage { position: relative; border-top: 1px solid var(--ho-line-strong); padding: .85rem .55rem 0 0; }
        .ho-stage::before {
            content: ""; position: absolute; width: .5rem; height: .5rem; border-radius: 50%;
            top: -.28rem; left: 0; background: var(--ho-green); box-shadow: 0 0 12px rgba(32,178,107,.5);
        }
        .ho-stage small { display: block; color: #8798b0; font: 700 .62rem/1 ui-monospace, monospace; }
        .ho-stage b { display: block; color: #30445f; margin-top: .45rem; font-size: .75rem; }

        .ho-memory {
            border: 1px solid rgba(35, 104, 232, .18);
            background: rgba(255, 255, 255, .78);
            padding: 1rem;
            margin-bottom: .7rem;
            border-radius: 12px;
        }
        .ho-memory-head { display: flex; justify-content: space-between; gap: 1rem; }
        .ho-memory-source { color: var(--ho-blue); font: 700 .67rem/1 ui-monospace, monospace; }
        .ho-memory-score { color: #7a8ba4; font: 600 .66rem/1 ui-monospace, monospace; }
        .ho-memory p { color: #42546d; font-size: .86rem; line-height: 1.5; margin: .8rem 0 0; }

        .ho-action {
            border-left: 2px solid var(--ho-blue);
            background: rgba(255, 255, 255, .74);
            padding: .85rem 1rem;
            margin-bottom: .55rem;
            border-radius: 0 10px 10px 0;
        }
        .ho-action--denied { border-left-color: var(--ho-red); }
        .ho-action b { color: var(--ho-text); font-size: .85rem; }
        .ho-action span { float: right; color: var(--ho-muted); font: 650 .65rem/1 ui-monospace, monospace; }
        .ho-action p { color: var(--ho-muted); font-size: .75rem; margin: .35rem 0 0; }

        [data-testid="stMetric"] {
            border-top: 1px solid var(--ho-line-strong);
            padding: .85rem .2rem .2rem;
        }
        [data-testid="stMetricLabel"] { color: var(--ho-muted); }
        [data-testid="stMetricValue"] { color: var(--ho-text); letter-spacing: -.045em; }
        [data-baseweb="tab-list"] { gap: .2rem; border-bottom: 1px solid var(--ho-line); }
        [data-baseweb="tab"] { color: var(--ho-muted); font-size: .76rem; letter-spacing: .02em; }
        [aria-selected="true"] { color: var(--ho-blue) !important; }
        [data-testid="stDataFrame"] { border: 1px solid var(--ho-line); border-radius: 12px; overflow: hidden; }
        [data-testid="stExpander"] {
            border: 1px solid var(--ho-line); background: rgba(255, 255, 255, .72); border-radius: 12px;
        }

        .stButton > button {
            border-radius: 10px;
            min-height: 2.8rem;
            border: 1px solid var(--ho-line-strong);
            background: rgba(255, 255, 255, .08);
            color: var(--ho-text);
            font-weight: 650;
        }
        .stButton > button[kind="primary"] {
            background: var(--ho-blue);
            border-color: var(--ho-blue);
            color: #ffffff;
        }
        .stButton > button:hover { border-color: var(--ho-blue-bright); color: var(--ho-blue); }
        .stButton > button[kind="primary"]:hover { background: #1757c8; color: #ffffff; }
        [data-baseweb="select"] > div { background: var(--ho-panel-solid); border-color: var(--ho-line); }

        [data-testid="stSidebar"] .stButton > button { color: #dbe7f9; border-color: rgba(255,255,255,.18); }
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            color: #ffffff; background: var(--ho-blue-bright); border-color: var(--ho-blue-bright);
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            color: #f7faff; background: rgba(5, 14, 29, .42); border-color: rgba(255,255,255,.14);
        }
        [data-testid="stSidebar"] svg { fill: #b7c5d9; }

        .ho-provider-list { display: grid; gap: .62rem; margin: .85rem 0 1rem; }
        .ho-provider { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
        .ho-provider-name { color: #b9c7da; font-size: .79rem; }
        .ho-provider-state {
            display: inline-flex; align-items: center; gap: .42rem; color: #8090a8;
            font: 700 .62rem/1 ui-monospace, monospace; letter-spacing: .06em; text-transform: uppercase;
        }
        .ho-provider-dot { width: .42rem; height: .42rem; border-radius: 50%; background: #687994; }
        .ho-provider--active .ho-provider-state { color: #77e5ae; }
        .ho-provider--active .ho-provider-dot {
            background: var(--ho-green); box-shadow: 0 0 10px rgba(32,178,107,.75);
        }

        @keyframes ho-pulse { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
        @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] { padding: 2rem 1rem 4rem; }
            .ho-grid--3, .ho-grid--4 { grid-template-columns: 1fr; }
            .ho-pipeline { grid-template-columns: repeat(3, 1fr); row-gap: 1.4rem; }
            .ho-hero-top { display: block; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    """Render the product proposition and immutable simulation boundary."""
    st.markdown(
        '<div class="ho-kicker">Physical intelligence / verified autonomy</div>',
        unsafe_allow_html=True,
    )
    st.title("Handsoff")
    st.markdown(
        '<p class="ho-deck"><strong>State the outcome.</strong> Handsoff compiles the goal, '
        "checks every proposed action against deterministic policy, and proves what actually "
        "happened.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="ho-badge-row">
          <div class="ho-badge ho-badge--live"><i class="ho-dot"></i> Runtime online</div>
          <div class="ho-badge">Local-first</div>
          <div class="ho-badge">Simulation only</div>
          <div class="ho-badge">Model ≠ controller</div>
        </div>
        <div class="ho-notice"><b>SIM / 00</b><span>No real devices, Home Assistant writes,
        vehicle actions, or safety-critical actuation are connected.</span></div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar(session: DemoSession) -> tuple[str, DemoMode]:
    """Render committed missions and explicit provider compositions."""
    settings = session.facade.settings
    options = session.facade.scenarios()
    by_id = {option.scenario_id: option for option in options}
    modes = tuple(DemoMode)

    st.sidebar.markdown('<div class="ho-kicker">Mission control</div>', unsafe_allow_html=True)
    st.sidebar.markdown("### Configure a run")
    scenario_id = st.sidebar.selectbox(
        "Reference mission",
        options=tuple(by_id),
        format_func=lambda value: by_id[value].title,
        key="scenario_id",
    )
    mode = st.sidebar.selectbox(
        "Intelligence layer",
        options=modes,
        index=modes.index(DemoMode.SYNTHETIC_MEMORY),
        format_func=lambda value: value.label,
        key="demo_mode",
    )
    st.sidebar.caption(by_id[scenario_id].description)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Provider fabric**")
    gemini_class = " ho-provider--active" if settings.gemini_available else ""
    memory_class = " ho-provider--active" if settings.supermemory_available else ""
    gemini_state = "Ready" if settings.gemini_available else "Offline"
    memory_state = "Read only" if settings.supermemory_available else "Offline"
    st.sidebar.markdown(
        f"""
        <div class="ho-provider-list">
          <div class="ho-provider{gemini_class}"><span class="ho-provider-name">Gemini</span>
          <span class="ho-provider-state"><i class="ho-provider-dot"></i>{gemini_state}</span></div>
          <div class="ho-provider{memory_class}"><span class="ho-provider-name">Supermemory</span>
          <span class="ho-provider-state"><i class="ho-provider-dot"></i>{memory_state}</span></div>
          <div class="ho-provider ho-provider--active"><span class="ho-provider-name">Synthetic context</span>
          <span class="ho-provider-state"><i class="ho-provider-dot"></i>Ready</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("No credential values or raw provider responses enter the browser surface.")

    run_clicked = st.sidebar.button(
        "Run bounded mission →", type="primary", use_container_width=True
    )
    reset_clicked = st.sidebar.button("Reset evidence", use_container_width=True)
    if reset_clicked:
        session.reset()
        st.rerun()
    if run_clicked:
        session.run(scenario_id, mode)
    return scenario_id, mode


def _render_section_label(index: str, label: str) -> None:
    """Render a numbered editorial section divider."""
    st.markdown(
        f'<div class="ho-section-label"><span>〉 {escape(label)}</span><span>[{escape(index)} / 07]</span></div>',
        unsafe_allow_html=True,
    )


def _render_landing(scenario: ScenarioDefinition, mode: DemoMode) -> None:
    """Explain the runnable system before evidence exists."""
    st.info("Mission is staged. Run it from Mission control to generate a complete evidence trace.")
    _render_section_label("01", "Selected mission")
    st.markdown(
        f"""
        <div class="ho-hero-panel">
          <div class="ho-kicker">{escape(mode.label)} / no actuation</div>
          <div class="ho-result">{escape(scenario.title)}</div>
          <p class="ho-deck">{escape(scenario.goal.objective)}</p>
          <div class="ho-caption">{len(scenario.capabilities):02d} declared capabilities ·
          {len(scenario.goal.acceptance_conditions):02d} acceptance conditions ·
          immutable fixture clock</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_section_label("02", "One goal, six hard boundaries")
    stages = (
        ("01", "Observe", "Fresh, sourced world state"),
        ("02", "Remember", "Preference context only"),
        ("03", "Propose", "Typed and untrusted"),
        ("04", "Authorize", "Deterministic policy"),
        ("05", "Execute", "Allowlisted simulator"),
        ("06", "Verify", "Independent evidence"),
    )
    cards = "".join(
        f'<div class="ho-card"><span class="ho-card-num">{number}</span><h3>{title}</h3><p>{body}</p></div>'
        for number, title, body in stages
    )
    st.markdown(f'<div class="ho-grid ho-grid--3">{cards}</div>', unsafe_allow_html=True)
    _render_section_label("03", "The control-plane thesis")
    st.markdown(
        """
        <div class="ho-grid ho-grid--3">
          <div class="ho-card"><span class="ho-card-num">GOAL</span><h3>Intent, not commands</h3>
          <p>The human defines an outcome and observable acceptance conditions.</p></div>
          <div class="ho-card"><span class="ho-card-num">POLICY</span><h3>Authority stays deterministic</h3>
          <p>Models and memory can shape a proposal. Neither can grant permission.</p></div>
          <div class="ho-card"><span class="ho-card-num">EVIDENCE</span><h3>Reality closes the loop</h3>
          <p>Adapter acceptance is not success. Fresh observations prove the effect.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary(run: DemoRun) -> None:
    """Render the executive outcome without recomputing authority."""
    runtime = run.assessment.runtime
    decision = runtime.policy.decision.value
    result_class = "ho-result--allow" if decision == "allow" else "ho-result--deny"
    match_label = "TRACE MATCHED" if run.assessment.matched else "TRACE MISMATCH"
    _render_section_label("01", "Mission outcome")
    st.markdown(
        f"""
        <div class="ho-hero-panel">
          <div class="ho-hero-top">
            <div><div class="ho-kicker">{match_label}</div>
            <div class="ho-result {result_class}">{escape(_humanize(runtime.terminal_plan_state.value))}</div></div>
            <div class="ho-badge">POLICY / {escape(decision.upper())}</div>
          </div>
          <p class="ho-deck">{escape(run.scenario.goal.objective)}</p>
          <div class="ho-caption">Planner {escape(runtime.planner.provider)} / {escape(runtime.planner.model)} ·
          trusted-input fingerprint {escape(run.trusted_input_fingerprint)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if run.assessment.matched:
        st.success("Observed runtime evidence matches the committed scenario vector.")
    else:
        st.error("Observed runtime evidence differs from the committed scenario vector.")

    columns = st.columns(4)
    columns[0].metric("Policy", _humanize(decision))
    columns[1].metric("Terminal state", _humanize(runtime.terminal_plan_state.value))
    columns[2].metric("Evidence events", len(runtime.events))
    columns[3].metric("Verified goals", sum(item.satisfied for item in runtime.verifications))

    stages = (
        ("01", "Goal"),
        ("02", "Context"),
        ("03", "Proposal"),
        ("04", "Policy"),
        ("05", "Execution"),
        ("06", "Evidence"),
    )
    pipeline = "".join(
        f'<div class="ho-stage"><small>{number}</small><b>{label}</b></div>'
        for number, label in stages
    )
    st.markdown(f'<div class="ho-pipeline">{pipeline}</div>', unsafe_allow_html=True)


def _render_overview(run: DemoRun) -> None:
    """Render a narrative mission brief and action outcome strip."""
    runtime = run.assessment.runtime
    st.subheader("From objective to observed outcome")
    st.caption("Every card below is derived from the typed runtime result.")
    cards = (
        ("GOAL", "Human intent", run.scenario.goal.objective),
        ("CONTEXT", "Preference memory", f"{len(run.memory.items)} bounded item(s)"),
        ("AUTHORITY", "Policy kernel", _humanize(runtime.policy.decision.value)),
        ("EVIDENCE", "Terminal truth", _humanize(runtime.terminal_plan_state.value)),
    )
    markup = "".join(
        f'<div class="ho-card"><span class="ho-card-num">{escape(kind)}</span>'
        f"<h3>{escape(title)}</h3><p>{escape(body)}</p></div>"
        for kind, title, body in cards
    )
    st.markdown(f'<div class="ho-grid ho-grid--4">{markup}</div>', unsafe_allow_html=True)
    st.markdown("#### Capability outcome")
    decisions = {item.action_id: item for item in runtime.policy.action_decisions}
    for action in runtime.planner.plan.actions:
        decision = decisions[action.action_id]
        denied = " ho-action--denied" if decision.decision.value == "deny" else ""
        st.markdown(
            f'<div class="ho-action{denied}"><b>{escape(action.capability_id)}</b>'
            f"<span>{escape(decision.decision.value.upper())}</span>"
            f"<p>{escape('; '.join(decision.reasons))}</p></div>",
            unsafe_allow_html=True,
        )


def _render_plan(run: DemoRun) -> None:
    """Render the untrusted proposal and declared action contracts."""
    plan = run.assessment.runtime.planner.plan
    st.subheader("Typed proposal / untrusted by design")
    st.caption("Schema validity makes a proposal inspectable. It does not make it authorized.")
    st.dataframe(
        [
            {
                "action": action.action_id,
                "capability": action.capability_id,
                "target": action.target_entity_id,
                "dependencies": ", ".join(action.depends_on) or "—",
                "failure strategy": action.on_failure.value,
            }
            for action in plan.actions
        ],
        width="stretch",
        hide_index=True,
    )
    with st.expander("Inspect the complete plan contract"):
        st.json(plan.model_dump(mode="json"), expanded=False)


def _render_policy(run: DemoRun) -> None:
    """Render deterministic plan and action policy decisions."""
    policy = run.assessment.runtime.policy
    st.subheader("The model stops here")
    st.caption("Policy uses only trusted goals, observations, and capability contracts.")
    st.markdown(
        f'<div class="ho-hero-panel"><div class="ho-kicker">Policy kernel / v{escape(policy.policy_version)}</div>'
        f'<div class="ho-result">{escape(_humanize(policy.decision.value))}</div>'
        f'<div class="ho-caption">{escape("; ".join(policy.reasons))}</div></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        [
            {
                "action": decision.action_id,
                "risk": decision.risk_class.value,
                "decision": decision.decision.value,
                "reason": "; ".join(decision.reasons),
            }
            for decision in policy.action_decisions
        ],
        width="stretch",
        hide_index=True,
    )


def _render_execution(run: DemoRun) -> None:
    """Render plan and action state transitions without issuing commands."""
    runtime = run.assessment.runtime
    st.subheader("Execution is a state machine, not a promise")
    st.caption("Every transition is legal, timestamped, and ledger-backed.")
    st.markdown("#### Plan lifecycle")
    st.dataframe(
        [transition.model_dump(mode="json") for transition in runtime.plan_transitions],
        width="stretch",
        hide_index=True,
    )
    st.markdown("#### Action lifecycle")
    st.dataframe(
        [transition.model_dump(mode="json") for transition in runtime.action_transitions],
        width="stretch",
        hide_index=True,
    )


def _render_verification(run: DemoRun) -> None:
    """Render independent condition evidence after simulated dispatch."""
    results = run.assessment.runtime.verifications
    satisfied = sum(item.satisfied for item in results)
    st.subheader("Reality is the completion signal")
    st.caption("An accepted adapter request never counts as physical-effect evidence.")
    st.markdown(
        f'<div class="ho-hero-panel"><div class="ho-kicker">Independent verifier</div>'
        f'<div class="ho-result">{satisfied:02d} / {len(results):02d}</div>'
        '<div class="ho-caption">Acceptance conditions supported by fresh observations</div></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        [item.model_dump(mode="json") for item in results],
        width="stretch",
        hide_index=True,
    )


def _render_evidence(run: DemoRun) -> None:
    """Render the source observations and ordered evidence ledger."""
    runtime = run.assessment.runtime
    observations = [
        event.payload.model_dump(mode="json")
        for event in runtime.events
        if event.kind is EventKind.OBSERVATION_RECORDED
    ]
    st.subheader("Evidence vault")
    st.caption("The ledger is append-only; the UI is a projection over its typed records.")
    st.markdown("#### Timestamped world evidence")
    st.dataframe(observations, width="stretch", hide_index=True)
    st.markdown("#### Ordered event ledger")
    st.dataframe(
        [
            {
                "sequence": event.sequence_number,
                "kind": event.kind.value,
                "occurred at": event.occurred_at.isoformat(),
                "subject": event.payload.__class__.__name__,
                "event": event.event_id,
            }
            for event in runtime.events
        ],
        width="stretch",
        hide_index=True,
    )


def _render_memory(run: DemoRun) -> None:
    """Render bounded context and make its lack of authority explicit."""
    memory = run.memory
    synthetic = memory.provider == "synthetic"
    mode_label = "OFFLINE / SYNTHETIC" if synthetic else "READ ONLY / EXTERNAL"
    st.subheader("Context without control")
    st.caption("Memory helps a planner understand preference. Policy decides what may happen.")
    st.markdown(
        f"""
        <div class="ho-grid ho-grid--3">
          <div class="ho-card"><span class="ho-card-num">SOURCE</span><h3>{escape(memory.provider)}</h3>
          <p>{escape(mode_label)}</p></div>
          <div class="ho-card"><span class="ho-card-num">BOUND</span><h3>{len(memory.items)} / 5</h3>
          <p>Normalized context items</p></div>
          <div class="ho-card"><span class="ho-card-num">AUTHORITY</span><h3>None</h3>
          <p>Cannot add capabilities, approve, dispatch, or verify</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Retrieved context")
    if memory.items:
        for item in memory.items:
            st.markdown(
                f'<div class="ho-memory"><div class="ho-memory-head">'
                f'<span class="ho-memory-source">{escape(item.source_id)}</span>'
                f'<span class="ho-memory-score">RELEVANCE {item.relevance:.2f}</span></div>'
                f"<p>{escape(item.text)}</p></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No context was supplied to this proposal.")
    if synthetic:
        st.caption(
            "Synthetic records are committed local fixtures for a complete no-key demo. "
            "No Supermemory request was made."
        )
    elif memory.used_fallback:
        st.caption("The provider was unavailable; the runtime failed closed to empty context.")
    st.code(f"trusted authority inputs: {run.trusted_input_fingerprint}", language="text")


def main() -> None:
    """Render the complete public operator surface."""
    st.set_page_config(
        page_title="Handsoff — Verified autonomy",
        page_icon="◼",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_design_system()
    _render_header()
    session = _session()
    scenario_id, mode = _render_sidebar(session)
    run = session.last_run
    if run is None:
        _render_landing(session.facade.scenario(scenario_id), mode)
        return

    _render_summary(run)
    _render_section_label("02", "Inspectable runtime")
    tabs = st.tabs(
        ["Overview", "Proposal", "Policy", "Execution", "Verification", "Evidence", "Memory"],
    )
    renderers = (
        _render_overview,
        _render_plan,
        _render_policy,
        _render_execution,
        _render_verification,
        _render_evidence,
        _render_memory,
    )
    for tab, renderer in zip(tabs, renderers, strict=True):
        with tab:
            renderer(run)


if __name__ == "__main__":
    main()
