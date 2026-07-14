"""Browser-session-owned state for Streamlit reruns."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.presentation.facade import DemoFacade, DemoMode, DemoRun


class DemoSession:
    """Keep one browser's last result out of process-global state."""

    def __init__(self, facade: DemoFacade) -> None:
        """Initialize an empty independent session."""
        self._facade = facade
        self._last_run: DemoRun | None = None

    @property
    def facade(self) -> DemoFacade:
        """Return this session's immutable composition root."""
        return self._facade

    @property
    def last_run(self) -> DemoRun | None:
        """Return only this session's most recent result."""
        return self._last_run

    def run(self, scenario_id: str, mode: DemoMode) -> DemoRun:
        """Execute with fresh runtime state and retain the inspectable result."""
        self._last_run = self._facade.run(scenario_id, mode)
        return self._last_run

    def reset(self) -> None:
        """Discard the presentation result; subsequent execution reconstructs state."""
        self._last_run = None


__all__ = ["DemoSession"]
