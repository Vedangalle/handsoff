"""Handsoff Streamlit mission-control demonstration."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, cast

import streamlit as st

from handsoff.domain.events import EventKind
from handsoff.presentation import (
    DemoComparison,
    DemoFacade,
    DemoMode,
    DemoRun,
    DemoSession,
    DemoSettings,
    EcosystemView,
    build_ecosystem_view,
)

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
            padding: 2.15rem 3.2rem 5rem;
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
            font-size: clamp(3.5rem, 6vw, 6.15rem) !important;
            line-height: .92 !important;
            margin: .15rem 0 .55rem !important;
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
            margin-bottom: .72rem;
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
            font-size: clamp(1.02rem, 1.65vw, 1.3rem);
            line-height: 1.48;
            margin: 0 0 1rem;
        }
        .ho-deck strong { color: var(--ho-text); font-weight: 600; }
        .ho-rule { border-top: 1px solid var(--ho-line); margin: 2.2rem 0; }

        .ho-badge-row { display: flex; flex-wrap: wrap; gap: .55rem; margin: .8rem 0 1.35rem; }
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
            margin: .65rem 0 1.15rem;
            border-radius: 12px;
        }
        .ho-notice b { color: var(--ho-amber); font-family: ui-monospace, monospace; }

        .ho-section-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--ho-line);
            padding: .8rem 0 1rem;
            margin-top: 1.35rem;
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

        .ho-compare-hero {
            display: grid;
            grid-template-columns: 1.15fr .85fr;
            gap: 1rem;
            align-items: stretch;
            margin: .15rem 0 1rem;
        }
        .ho-compare-pane {
            border: 1px solid var(--ho-line);
            background: rgba(255, 255, 255, .82);
            border-radius: 16px;
            padding: 1.25rem;
            box-shadow: 0 12px 34px rgba(36, 88, 168, .055);
        }
        .ho-compare-pane--context {
            background: linear-gradient(145deg, rgba(238, 245, 255, .98), rgba(255, 255, 255, .9));
            border-color: rgba(35, 104, 232, .25);
        }
        .ho-compare-label {
            color: var(--ho-blue);
            font: 700 .65rem/1 ui-monospace, monospace;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .ho-compare-pane h3 { margin: .7rem 0 .35rem; font-size: 1.22rem !important; }
        .ho-compare-pane p { color: var(--ho-muted); margin: 0; font-size: .82rem; }
        .ho-proof-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .65rem; }
        .ho-proof {
            border-top: 2px solid var(--ho-green);
            background: rgba(255, 255, 255, .78);
            padding: .9rem;
            border-radius: 4px 4px 12px 12px;
        }
        .ho-proof--changed { border-top-color: var(--ho-blue); }
        .ho-proof b { display: block; color: var(--ho-text); font-size: .78rem; }
        .ho-proof span { display: block; color: var(--ho-muted); font-size: .69rem; margin-top: .4rem; }

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
            .ho-compare-hero, .ho-proof-grid { grid-template-columns: 1fr; }
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

    compare_clicked = st.sidebar.button(
        "Run judge comparison →", type="primary", use_container_width=True
    )
    run_clicked = st.sidebar.button("Run selected mode", use_container_width=True)
    reset_clicked = st.sidebar.button("Reset evidence", use_container_width=True)
    if reset_clicked:
        session.reset()
        st.rerun()
    if run_clicked:
        session.run(scenario_id, mode)
    if compare_clicked:
        session.compare(scenario_id)
    return scenario_id, mode


def _render_section_label(index: str, label: str) -> None:
    """Render a numbered editorial section divider."""
    st.markdown(
        f'<div class="ho-section-label"><span>〉 {escape(label)}</span><span>[{escape(index)} / 07]</span></div>',
        unsafe_allow_html=True,
    )


def _render_ecosystem(view: EcosystemView) -> None:
    """Render the evidence-driven whole-home cutaway and local inspector."""
    devices = [
        {
            "id": device.device_id,
            "label": device.label,
            "room": device.room,
            "status": device.status.value,
            "value": device.value,
            "detail": device.detail,
        }
        for device in view.devices
    ]
    payload = json.dumps(devices, separators=(",", ":")).replace("</", "<\\/")
    status_by_id = {device.device_id: device.status.value for device in view.devices}
    scene_classes = " ".join(f"{device_id}-{status}" for device_id, status in status_by_id.items())
    mission_label = _humanize(view.mission_state)
    _render_section_label("01", "One home / one coordinated system")
    # Ruff's SQL heuristic sees SELECT in the JavaScript below; this is local HTML, not SQL.
    component = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        * {{ box-sizing: border-box; }}
        :root {{
          --ink:#0c1830; --muted:#63738a; --blue:#2368e8; --blue2:#4d8fff;
          --green:#20b26b; --red:#d84d5b; --amber:#cf8614; --line:rgba(27,70,135,.14);
          font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        body {{ margin:0; color:var(--ink); background:transparent; }}
        .ecosystem {{
          position:relative; height:700px; overflow:hidden; border:1px solid var(--line);
          border-radius:24px;
          background:
            radial-gradient(circle at 82% 18%,rgba(255,255,255,.96) 0 54px,transparent 55px),
            radial-gradient(circle at 18% 72%,rgba(89,148,255,.1),transparent 240px),
            linear-gradient(160deg,#fbfdff 0%,#edf5ff 55%,#e4edf8 100%);
          box-shadow:0 28px 80px rgba(35,75,137,.12),inset 0 1px 0 rgba(255,255,255,.9);
        }}
        .ecosystem::before {{
          content:"";position:absolute;inset:0;pointer-events:none;opacity:.34;
          background-image:linear-gradient(rgba(35,104,232,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(35,104,232,.035) 1px,transparent 1px);
          background-size:44px 44px;mask-image:linear-gradient(to bottom,transparent 4%,#000 34%,transparent 92%);
        }}
        .topbar {{
          position:absolute; z-index:12; top:20px; left:24px; right:24px; display:flex;
          align-items:flex-start; justify-content:space-between; gap:20px; pointer-events:none;
        }}
        .eyebrow {{ color:var(--blue); font:800 10px/1 ui-monospace,monospace; letter-spacing:.15em; text-transform:uppercase; }}
        h1 {{ margin:8px 0 0; font-size:clamp(28px,3.4vw,44px); line-height:1; letter-spacing:-.052em; }}
        .mission {{
          display:flex; align-items:center; gap:8px; padding:9px 12px; border:1px solid var(--line);
          border-radius:999px; background:rgba(255,255,255,.8); color:#41516a;
          font:800 10px/1 ui-monospace,monospace; letter-spacing:.08em; text-transform:uppercase;
          backdrop-filter:blur(12px);
        }}
        .mission i {{ width:8px; height:8px; border-radius:50%; background:var(--green); box-shadow:0 0 12px rgba(32,178,107,.58); }}
        .scene {{ position:absolute; inset:0; }}
        .house-svg {{ width:100%; height:100%; display:block; filter:saturate(1.04) contrast(1.01); }}
        .flow {{ opacity:.16;stroke-dasharray:8 12; }}
        .scene.succeeded .flow {{ opacity:.62;animation:flow 1.7s linear infinite; }}
        .scene.succeeded .arrival-car {{ animation:driveIn 1.35s cubic-bezier(.2,.8,.2,1) both; }}
        .tv-on,.coffee-steam,.light-glow,.fan-blades,.garage-open,.ice-cubes,.comfort-wave,.charger-pulse {{ opacity:0; }}
        .garage-verified .garage-closed {{ animation:doorLift .72s cubic-bezier(.4,0,.2,1) 1.05s both; }}
        .garage-verified .garage-open {{ animation:reveal .3s ease-out 1.2s both; }}
        .charger-verified .charger-pulse {{ animation:powerPulse 1.35s ease-in-out 1.65s infinite; }}
        .climate-verified .comfort-wave {{ animation:comfort 2.4s ease-out 2s infinite; }}
        .lighting-verified .light-glow {{ animation:glow 2.2s ease-in-out 2.15s infinite,reveal .35s ease-out 2.15s both; }}
        .light-fixture {{ fill:#d7e0ea; }}
        .lighting-verified .light-fixture {{ animation:fixtureOn .35s ease-out 2.15s both; }}
        .fan-verified .fan-blades {{
          transform-box:fill-box;transform-origin:center;
          animation:reveal .35s ease-out 2.55s both,spin 2.4s linear 2.55s infinite;
        }}
        .ice-verified .ice-cubes {{ animation:iceDrop 1.4s ease-in-out 2.75s infinite,reveal .3s ease-out 2.75s both; }}
        .coffee-verified .coffee-steam {{ animation:steam 1.8s ease-in-out 3.05s infinite,reveal .3s ease-out 3.05s both; }}
        .media-verified .tv-on {{ animation:screenOn .85s ease-out 3.35s both; }}
        .device {{
          position:absolute; z-index:9; display:flex; align-items:center; gap:8px; min-height:30px;padding:8px 11px;
          color:#3f506a; background:rgba(255,255,255,.9); border:1px solid rgba(27,70,135,.16);
          border-radius:999px; box-shadow:0 8px 24px rgba(33,71,126,.1); cursor:pointer;
          font:800 10px/1 ui-monospace,monospace; letter-spacing:.05em; text-transform:uppercase;
          transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease; white-space:nowrap;
        }}
        .device:hover,.device.active {{ transform:translateY(-2px) scale(1.03); border-color:var(--blue2); box-shadow:0 10px 30px rgba(35,104,232,.2); }}
        .device .dot {{ width:8px; height:8px; border-radius:50%; background:#99a5b7; }}
        .device[data-status="ready"] .dot,.device[data-status="verified"] .dot {{ background:var(--green); box-shadow:0 0 10px rgba(32,178,107,.7); }}
        .device[data-status="verified"] {{ animation:arrive .65s ease-out both; animation-delay:calc(.7s + var(--delay)); }}
        .device[data-status="blocked"] .dot,.device[data-status="failed"] .dot {{ background:var(--red); box-shadow:0 0 10px rgba(216,77,91,.5); }}
        .device[data-status="prohibited"] .dot {{ background:var(--amber); }}
        .vehicle {{ left:4%; top:72%; }} .grid {{ left:8%; top:31%; }} .garage {{ left:25%; top:64%; }}
        .charger {{ left:39%; top:75%; }} .coffee {{ left:48%; top:58%; }} .ice {{ left:57%; top:42%; }}
        .climate {{ left:66%; top:28%; }} .lighting {{ left:73%; top:15%; }} .fan {{ left:73%; top:42%; }}
        .media {{ left:79%; top:60%; }} .fireplace {{ left:86%; top:70%; }}
        .inspector {{
          position:absolute; z-index:10; right:22px; bottom:18px; width:min(420px,43%); min-height:112px;
          padding:14px 16px 12px; border:1px solid rgba(27,70,135,.16); border-radius:16px;
          background:rgba(255,255,255,.9); box-shadow:0 18px 50px rgba(26,62,116,.13); backdrop-filter:blur(14px);
        }}
        .inspector-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
        .inspector h2 {{ margin:0; font-size:18px; letter-spacing:-.03em; }}
        .state {{ color:var(--green); font:800 9px/1 ui-monospace,monospace; letter-spacing:.1em; text-transform:uppercase; }}
        .inspector.status-blocked .state,.inspector.status-failed .state {{ color:var(--red); }}
        .inspector.status-prohibited .state {{ color:var(--amber); }}
        .inspector p {{ margin:8px 0 0; color:var(--muted); font-size:12px; line-height:1.45; }}
        .value {{ color:var(--blue); font-weight:750; }}
        .sequence {{ display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-top:10px; }}
        .sequence span {{
          position:relative;padding-top:7px;border-top:2px solid #d9e2ef;color:#8b99ac;
          font:750 7px/1 ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;
        }}
        .sequence span::before {{ content:"";position:absolute;top:-4px;left:0;width:6px;height:6px;border-radius:50%;background:#b8c4d4; }}
        .scene.succeeded .sequence span {{ animation:phaseOn .35s ease-out both;animation-delay:calc(.7s + var(--phase)); }}
        .legend {{
          position:absolute; z-index:7; left:24px; bottom:24px; display:flex; gap:12px; color:#718098;
          font:700 8px/1 ui-monospace,monospace; letter-spacing:.08em; text-transform:uppercase;
        }}
        .legend span {{ display:flex; align-items:center; gap:5px; }}
        .legend i {{ width:7px;height:7px;border-radius:50%;background:#99a5b7; }}
        .legend .live {{background:var(--green)}} .legend .stop {{background:var(--red)}} .legend .guard {{background:var(--amber)}}
        @keyframes flow {{ to {{ stroke-dashoffset:-40; }} }}
        @keyframes driveIn {{ from {{ transform:translateX(-220px);opacity:.2; }} to {{ transform:translateX(0);opacity:1; }} }}
        @keyframes doorLift {{ to {{ transform:translateY(-96px);opacity:0; }} }}
        @keyframes reveal {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
        @keyframes powerPulse {{ 0%,100% {{ opacity:.3;stroke-dashoffset:0; }} 50% {{ opacity:1;stroke-dashoffset:-18; }} }}
        @keyframes comfort {{ 0% {{ opacity:0;transform:scale(.7); }} 35% {{ opacity:.75; }} 100% {{ opacity:0;transform:scale(1.45); }} }}
        @keyframes iceDrop {{ 0%,100% {{ transform:translateY(-3px); }} 50% {{ transform:translateY(5px); }} }}
        @keyframes arrive {{ from {{ opacity:0; transform:translateY(8px) scale(.96); }} }}
        @keyframes screenOn {{ from {{ opacity:0; }} 35% {{ opacity:.35; }} 50% {{ opacity:.08; }} to {{ opacity:1; }} }}
        @keyframes steam {{ 0%,100% {{ transform:translateY(2px);opacity:.3; }} 50% {{ transform:translateY(-6px);opacity:1; }} }}
        @keyframes glow {{ 0%,100% {{ opacity:.5; }} 50% {{ opacity:1; }} }}
        @keyframes fixtureOn {{ from {{ fill:#d7e0ea; }} to {{ fill:#ffd56d; }} }}
        @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
        @keyframes phaseOn {{ to {{ color:#147d4d;border-color:rgba(32,178,107,.65); }} }}
        @keyframes phaseOnDot {{ to {{ background:var(--green);box-shadow:0 0 8px rgba(32,178,107,.7); }} }}
        .scene.succeeded .sequence span::before {{ animation:phaseOnDot .35s ease-out both;animation-delay:calc(.7s + var(--phase)); }}
        @media (max-width:760px) {{
          .ecosystem {{ height:610px; }} .topbar {{ top:16px;left:16px;right:16px; }}
          .house-svg {{ transform:scale(1.18); transform-origin:52% 62%; }}
          .device {{ min-height:26px;font-size:0;padding:7px; }} .inspector {{ right:14px;bottom:14px;width:calc(100% - 28px); }}
          .legend {{ display:none; }}
        }}
        @media (prefers-reduced-motion:reduce) {{ * {{ animation:none!important;transition:none!important; }} }}
      </style>
    </head>
    <body>
      <main class="ecosystem" aria-label="Interactive whole-home ecosystem">
        <div class="topbar"><div><div class="eyebrow">Handsoff / spatial runtime</div>
          <h1>The whole home moves as one.</h1></div>
          <div class="mission"><i></i>{escape(mission_label)}</div></div>
        <div class="scene {escape(view.mission_state)} {escape(scene_classes)}">
          <svg class="house-svg" viewBox="0 0 1200 700" role="img" aria-label="Cutaway smart home with driveway, garage, kitchen, living room, and utility systems">
            <defs>
              <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#e8f1ff"/><stop offset="1" stop-color="#f9fbff"/></linearGradient>
              <linearGradient id="home" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff"/><stop offset="1" stop-color="#eef4fd"/></linearGradient>
              <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eef8ff"/><stop offset=".5" stop-color="#cbe4ff"/><stop offset="1" stop-color="#edf7ff"/></linearGradient>
              <filter id="shadow"><feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#234c86" flood-opacity=".16"/></filter>
              <filter id="deep-shadow"><feDropShadow dx="0" dy="22" stdDeviation="20" flood-color="#163660" flood-opacity=".22"/></filter>
              <filter id="soft"><feGaussianBlur stdDeviation="16"/></filter>
            </defs>
            <rect width="1200" height="700" fill="url(#sky)"/>
            <circle cx="1010" cy="118" r="68" fill="#fff" opacity=".82"/>
            <path d="M0 548 Q180 510 360 548 T760 548 T1200 532 V700 H0Z" fill="#dce8f4"/>
            <path d="M0 590 L355 540 L550 568 L0 655Z" fill="#c8d5e5"/>
            <ellipse cx="655" cy="575" rx="370" ry="43" fill="#7794b9" opacity=".14" filter="url(#soft)"/>
            <path class="flow" d="M125 522 C220 470 280 480 340 465 S520 375 610 420 S780 370 920 400" fill="none" stroke="#3d7ff0" stroke-width="3" opacity=".48"/>
            <g filter="url(#deep-shadow)">
              <path d="M305 235 L635 92 L1008 236 Z" fill="#173765"/>
              <path d="M342 225 L634 110 L965 225 Z" fill="#2b66bd" opacity=".88"/>
              <path d="M363 216 L634 120 L944 216" fill="none" stroke="#5e98ee" stroke-width="3" opacity=".6"/>
              <rect x="318" y="226" width="675" height="360" rx="8" fill="url(#home)" stroke="#adc3df"/>
              <rect x="334" y="382" width="260" height="188" rx="4" fill="#e9f0f8" stroke="#bdcde0"/>
              <rect x="610" y="382" width="185" height="188" rx="4" fill="#fff8ef" stroke="#ddcdb9"/>
              <rect x="811" y="382" width="166" height="188" rx="4" fill="#f2f6ff" stroke="#c4d1e5"/>
              <rect x="463" y="244" width="226" height="122" rx="4" fill="#f7f0ff" stroke="#d5c6e4"/>
              <rect x="705" y="244" width="272" height="122" rx="4" fill="#eef7ff" stroke="#c4d9e8"/>
              <path d="M318 372H993M600 372V586M802 372V586" stroke="#fff" stroke-width="5" opacity=".75"/>
            </g>
            <text x="345" y="403" fill="#74849a" font-size="11" font-family="monospace">GARAGE</text>
            <text x="621" y="403" fill="#8b7967" font-size="11" font-family="monospace">KITCHEN</text>
            <text x="822" y="403" fill="#74849a" font-size="11" font-family="monospace">LIVING</text>
            <text x="474" y="264" fill="#8b7c98" font-size="11" font-family="monospace">REST</text>
            <text x="716" y="264" fill="#70869a" font-size="11" font-family="monospace">CLIMATE + LIGHT</text>
            <g class="garage-closed"><rect x="352" y="430" width="205" height="140" rx="4" fill="#cbd7e5"/><path d="M352 458H557M352 486H557M352 514H557M352 542H557" stroke="#a7b7ca" stroke-width="3"/></g>
            <g class="garage-open"><rect x="352" y="430" width="205" height="140" rx="4" fill="#23344c"/><rect x="365" y="444" width="180" height="14" rx="3" fill="#8ea6c1"/></g>
            <g class="arrival-car"><g transform="translate(82 491)"><ellipse cx="102" cy="77" rx="108" ry="13" fill="#23476f" opacity=".18"/><path d="M12 42 Q21 15 57 13 H137 Q166 15 187 42 L202 51 V73 H0V54Z" fill="#2368e8"/><path d="M57 18H130Q150 20 164 40H40Q46 23 57 18Z" fill="url(#glass)"/><path d="M70 19L61 39M135 20L148 39" stroke="#fff" stroke-width="2" opacity=".65"/><circle cx="43" cy="72" r="17" fill="#17253b"/><circle cx="163" cy="72" r="17" fill="#17253b"/><circle cx="43" cy="72" r="7" fill="#60758f"/><circle cx="163" cy="72" r="7" fill="#60758f"/></g></g>
            <g transform="translate(520 466)"><rect width="22" height="82" rx="5" fill="#fff" stroke="#7ea0ca"/><circle cx="11" cy="18" r="5" fill="#20b26b"/><path d="M11 29V54Q12 67 27 66" fill="none" stroke="#2368e8" stroke-width="4"/><path class="charger-pulse" d="M11 29V54Q12 67 27 66" fill="none" stroke="#85b6ff" stroke-width="8" stroke-linecap="round" stroke-dasharray="8 10"/></g>
            <g transform="translate(624 470)"><path d="M0 58H157V97H0Z" fill="#d9b993"/><path d="M15 58V21H83V58" fill="#f0d7b8"/><rect x="105" y="26" width="35" height="32" rx="5" fill="#263a55"/><rect x="113" y="34" width="19" height="8" rx="2" fill="#4d8fff"/><path class="coffee-steam" d="M116 20Q108 10 116 0M128 20Q120 10 128 0" fill="none" stroke="#8497ad" stroke-width="3" stroke-linecap="round"/></g>
            <g transform="translate(740 430)"><rect width="42" height="113" rx="5" fill="#dbe7f4" stroke="#9cb2ca"/><path d="M0 50H42" stroke="#9cb2ca"/><circle cx="33" cy="61" r="3" fill="#2368e8"/><g class="ice-cubes" fill="#8cc8ff"><rect x="9" y="70" width="7" height="7" rx="2"/><rect x="20" y="78" width="7" height="7" rx="2"/><rect x="10" y="88" width="7" height="7" rx="2"/></g></g>
            <g transform="translate(836 442)"><rect width="115" height="70" rx="6" fill="#182942"/><rect class="tv-on" x="5" y="5" width="105" height="60" rx="4" fill="#2368e8"/><text class="tv-on" x="57" y="35" text-anchor="middle" fill="#fff" font-size="9" font-family="monospace">ORBIT SEVEN</text><path d="M57 70V82M37 82H77" stroke="#52657d" stroke-width="4"/></g>
            <g transform="translate(885 235)"><circle r="7" fill="#52657d"/><g class="fan-blades" fill="#6f88a7"><ellipse cx="0" cy="-28" rx="8" ry="25"/><ellipse cx="28" cy="0" rx="25" ry="8"/><ellipse cx="0" cy="28" rx="8" ry="25"/><ellipse cx="-28" cy="0" rx="25" ry="8"/></g><circle r="5" fill="#52657d"/></g>
            <g class="light-glow"><circle cx="760" cy="294" r="45" fill="#ffd56d" opacity=".23" filter="url(#soft)"/><circle cx="920" cy="294" r="45" fill="#ffd56d" opacity=".23" filter="url(#soft)"/></g>
            <g class="light-fixture"><path d="M744 276Q760 255 776 276Q776 291 767 299H753Q744 291 744 276Z"/><path d="M904 276Q920 255 936 276Q936 291 927 299H913Q904 291 904 276Z"/></g>
            <g transform="translate(903 522)"><rect width="52" height="48" rx="4" fill="#d5c3b5"/><path d="M7 42Q14 22 26 40Q35 14 45 42" fill="#bac1ca"/><path d="M18 31L26 18L34 31" fill="none" stroke="#cf8614" stroke-width="3"/><rect x="17" y="8" width="18" height="12" rx="4" fill="#fff"/><path d="M22 12V9Q22 4 26 4Q30 4 30 9V12" fill="none" stroke="#76869a" stroke-width="2"/></g>
            <g transform="translate(769 317)"><circle class="comfort-wave" r="26" fill="none" stroke="#4d8fff" stroke-width="2"/></g><g transform="translate(748 302)"><rect width="42" height="30" rx="7" fill="#fff" stroke="#7b9bc1"/><text x="21" y="20" text-anchor="middle" fill="#2368e8" font-size="10" font-family="monospace">22°</text></g>
            <path d="M254 205V430" stroke="#8aa6c7" stroke-width="3"/><path d="M242 208H266L254 183Z" fill="#2368e8"/><circle cx="254" cy="433" r="9" fill="#20b26b"/>
          </svg>
          {_device_buttons(view)}
          <section class="inspector" aria-live="polite"><div class="inspector-head"><h2 id="device-title">Whole-home system</h2><span class="state" id="device-state">Explore</span></div><p><span class="value" id="device-value">Select any room or device.</span><br><span id="device-detail">Every view is derived from scenario evidence and deterministic policy.</span></p><div class="sequence" aria-label="Arrival sequence"><span style="--phase:0s">Approach</span><span style="--phase:.45s">Entry</span><span style="--phase:.9s">Comfort</span><span style="--phase:1.35s">Kitchen</span><span style="--phase:1.8s">Media</span></div></section>
          <div class="legend"><span><i class="live"></i>ready / verified</span><span><i class="stop"></i>blocked / failed</span><span><i class="guard"></i>guarded</span></div>
        </div>
      </main>
      <script>
        const devices={payload};
        function selectDevice(id) {{
          const device=devices.find(item=>item.id===id);
          if(!device)return;
          document.querySelectorAll('.device').forEach(node=>node.classList.toggle('active',node.dataset.device===id));
          document.getElementById('device-title').textContent=device.label+' / '+device.room;
          document.getElementById('device-state').textContent=device.status;
          document.getElementById('device-value').textContent=device.value;
          document.getElementById('device-detail').textContent=device.detail;
          document.querySelector('.inspector').className='inspector status-'+device.status;
        }}
        const timers=[];
        function cancelSequence() {{ timers.splice(0).forEach(timer=>clearTimeout(timer)); }}
        document.querySelectorAll('.device').forEach(node=>node.addEventListener('click',()=>{{cancelSequence();selectDevice(node.dataset.device);}}));
        selectDevice(devices.find(item=>item.status==='verified')?.id || devices[0].id);
        const sequence=['vehicle','garage','charger','climate','lighting','fan','ice','coffee','media'];
        if({str(view.mission_state == "succeeded").lower()} && !matchMedia('(prefers-reduced-motion: reduce)').matches) {{
          sequence.forEach((id,index)=>timers.push(setTimeout(()=>selectDevice(id),850+index*430)));
        }}
      </script>
    </body>
    </html>
    """  # noqa: S608
    st.iframe(component, width="stretch", height=720)


def _device_buttons(view: EcosystemView) -> str:
    """Build fixed local interaction targets without accepting browser input."""
    delays = {device.device_id: index * 0.12 for index, device in enumerate(view.devices)}
    return "".join(
        f'<button class="device {escape(device.device_id)}" data-device="{escape(device.device_id)}" '
        f'data-status="{escape(device.status.value)}" style="--delay:{delays[device.device_id]:.2f}s">'
        f'<i class="dot"></i>{escape(device.label)}</button>'
        for device in view.devices
    )


def _render_landing(scenario: ScenarioDefinition, mode: DemoMode) -> None:
    """Explain the runnable system before evidence exists."""
    _render_ecosystem(build_ecosystem_view(scenario))
    st.info("Mission is staged. Run it from Mission control to generate a complete evidence trace.")
    _render_section_label("02", "Selected mission")
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
    _render_section_label("03", "One goal, six hard boundaries")
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
    _render_section_label("04", "The control-plane thesis")
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


def _render_comparison(comparison: DemoComparison) -> None:
    """Render provider influence and control invariants from two complete traces."""
    contextual = comparison.contextual
    planner = contextual.assessment.runtime.planner
    changed = comparison.changed_deltas
    provider_state = "Live provider path" if comparison.live_provider_path else "Safe fallback path"
    provider_detail = (
        "Gemini and Supermemory completed without fallback."
        if comparison.live_provider_path
        else "Unavailable providers degraded to deterministic planning and/or empty context."
    )
    _render_section_label("02", "Judge comparison / context versus control")
    st.markdown(
        f"""
        <div class="ho-compare-hero">
          <div class="ho-compare-pane">
            <div class="ho-compare-label">A / deterministic reference</div>
            <h3>{escape(comparison.baseline.assessment.runtime.planner.provider)}</h3>
            <p>No external context. Reproducible proposal, policy, simulation, and evidence.</p>
          </div>
          <div class="ho-compare-pane ho-compare-pane--context">
            <div class="ho-compare-label">B / Gemini + Supermemory</div>
            <h3>{escape(provider_state)}</h3>
            <p>{escape(provider_detail)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="ho-proof-grid">
          <div class="ho-proof"><b>Trusted inputs</b><span>{"MATCH" if comparison.trusted_inputs_match else "DIFFER"}</span></div>
          <div class="ho-proof"><b>Capability bound</b><span>{"PRESERVED" if comparison.contextual_capabilities_declared else "VIOLATED"}</span></div>
          <div class="ho-proof"><b>Policy result</b><span>{"MATCH" if comparison.policy_decision_match else "CHANGED"}</span></div>
          <div class="ho-proof"><b>Terminal state</b><span>{"MATCH" if comparison.terminal_states_match else "CHANGED"}</span></div>
          <div class="ho-proof"><b>Verification</b><span>{"MATCH" if comparison.verification_results_match else "CHANGED"}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Context may shape an untrusted typed proposal. It cannot change trusted world inputs, "
        "declare capabilities, grant authority, dispatch actions, or manufacture verification."
    )

    columns = st.columns(4)
    columns[0].metric("Recalled context", len(contextual.memory.items))
    columns[1].metric("Semantic changes", len(changed))
    columns[2].metric("Planner", planner.provider)
    columns[3].metric("Policy", _humanize(contextual.assessment.runtime.policy.decision.value))

    st.markdown("#### Proposal semantics")
    st.dataframe(
        [
            {
                "capability": delta.capability_id,
                "occurrence": delta.occurrence,
                "change": delta.change.value,
                "changed fields": ", ".join(delta.changed_fields) or "—",
                "baseline parameters": delta.baseline.parameters if delta.baseline else "—",
                "contextual parameters": delta.contextual.parameters if delta.contextual else "—",
            }
            for delta in comparison.proposal_deltas
        ],
        width="stretch",
        hide_index=True,
    )
    if changed:
        st.caption(
            "The table reports behavior-level differences only; generated IDs and timestamps "
            "are intentionally excluded."
        )
    else:
        st.caption(
            "No behavior-level difference was observed. This is expected when Gemini falls back "
            "or when context does not alter the typed proposal."
        )

    st.markdown("#### Recalled context supplied to the planner")
    if contextual.memory.items:
        for item in contextual.memory.items:
            st.markdown(
                f'<div class="ho-memory"><div class="ho-memory-head">'
                f'<span class="ho-memory-source">{escape(item.source_id)}</span>'
                f'<span class="ho-memory-score">RELEVANCE {item.relevance:.2f}</span></div>'
                f"<p>{escape(item.text)}</p></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No external context entered this trace; empty-context fallback was preserved.")


def _render_summary(run: DemoRun, index: str = "02") -> None:
    """Render the executive outcome without recomputing authority."""
    runtime = run.assessment.runtime
    decision = runtime.policy.decision.value
    result_class = "ho-result--allow" if decision == "allow" else "ho-result--deny"
    match_label = "TRACE MATCHED" if run.assessment.matched else "TRACE MISMATCH"
    _render_section_label(index, "Mission outcome")
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
    observations: list[dict[str, object]] = []
    for event in runtime.events:
        if event.kind is not EventKind.OBSERVATION_RECORDED:
            continue
        row = event.payload.model_dump(mode="json")
        value = row.get("value")
        row["value"] = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        observations.append(row)
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

    _render_ecosystem(build_ecosystem_view(run.scenario, run.assessment.runtime))
    comparison = session.last_comparison
    if comparison is None:
        _render_summary(run)
        runtime_index = "03"
    else:
        _render_comparison(comparison)
        _render_summary(run, "03")
        runtime_index = "04"
    _render_section_label(runtime_index, "Inspectable runtime")
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
