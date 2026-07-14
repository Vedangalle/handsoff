"""Typed presentation facade for the Streamlit demonstration."""

from handsoff.presentation.comparison import (
    ActionSemantics,
    DemoComparison,
    ProposalChange,
    ProposalDelta,
    compare_runs,
)
from handsoff.presentation.config import DemoSettings
from handsoff.presentation.ecosystem import (
    EcosystemDevice,
    EcosystemStatus,
    EcosystemView,
    build_ecosystem_view,
)
from handsoff.presentation.facade import DemoFacade, DemoMode, DemoRun, ScenarioOption
from handsoff.presentation.session import DemoSession

__all__ = [
    "ActionSemantics",
    "DemoComparison",
    "DemoFacade",
    "DemoMode",
    "DemoRun",
    "DemoSession",
    "DemoSettings",
    "EcosystemDevice",
    "EcosystemStatus",
    "EcosystemView",
    "ProposalChange",
    "ProposalDelta",
    "ScenarioOption",
    "build_ecosystem_view",
    "compare_runs",
]
