"""Tests for package-level Milestone 4 metadata."""

from handsoff import __version__


def test_package_version_matches_hackathon_milestone() -> None:
    """The importable package exposes the completed Milestone 4 version."""
    assert __version__ == "0.4.0"
