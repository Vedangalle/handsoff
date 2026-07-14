"""Tests for package-level Milestone 3 metadata."""

from handsoff import __version__


def test_package_version_matches_planner_milestone() -> None:
    """The importable package exposes the Milestone 3 version."""
    assert __version__ == "0.3.0"
