"""Tests for package-level Milestone 1 metadata."""

from handsoff import __version__


def test_package_version_matches_contract_milestone() -> None:
    """The importable package exposes the Milestone 1 version."""
    assert __version__ == "0.1.0"
