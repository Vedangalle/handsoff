"""Typed presentation facade for the Streamlit demonstration."""

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
    "DemoFacade",
    "DemoMode",
    "DemoRun",
    "DemoSession",
    "DemoSettings",
    "EcosystemDevice",
    "EcosystemStatus",
    "EcosystemView",
    "ScenarioOption",
    "build_ecosystem_view",
]
