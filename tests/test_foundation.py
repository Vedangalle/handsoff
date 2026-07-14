"""Tests for the Milestone 0 package foundation."""

from handsoff import __version__


def test_package_version_matches_project_foundation() -> None:
    """The importable package exposes the foundation version."""
    assert __version__ == "0.0.0"
