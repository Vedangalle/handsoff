"""Validate Milestone 3 repository invariants without reading credential files."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.3.0"
REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".env.example",
    ".gitignore",
    "src/handsoff/__init__.py",
    "src/handsoff/py.typed",
    "src/handsoff/domain/__init__.py",
    "src/handsoff/domain/goals.py",
    "src/handsoff/domain/plans.py",
    "src/handsoff/domain/capabilities.py",
    "src/handsoff/domain/observations.py",
    "src/handsoff/domain/policies.py",
    "src/handsoff/domain/execution.py",
    "src/handsoff/domain/events.py",
    "src/handsoff/domain/scenarios.py",
    "src/handsoff/domain/planning.py",
    "src/handsoff/ports/__init__.py",
    "src/handsoff/ports/clock.py",
    "src/handsoff/ports/planner.py",
    "src/handsoff/ports/capability_adapter.py",
    "src/handsoff/ports/repositories.py",
    "src/handsoff/ports/memory.py",
    "src/handsoff/application/world_model.py",
    "src/handsoff/application/capability_registry.py",
    "src/handsoff/application/evaluate_plan.py",
    "src/handsoff/application/execute_plan.py",
    "src/handsoff/application/verify_outcome.py",
    "src/handsoff/application/run_scenario.py",
    "src/handsoff/application/planner_evaluation.py",
    "src/handsoff/adapters/__init__.py",
    "src/handsoff/adapters/clock/__init__.py",
    "src/handsoff/adapters/clock/deterministic.py",
    "src/handsoff/adapters/planner/deterministic.py",
    "src/handsoff/adapters/planner/gemini.py",
    "src/handsoff/adapters/planner/fallback.py",
    "src/handsoff/adapters/devices/simulator/adapter.py",
    "src/handsoff/adapters/persistence/memory.py",
    "src/handsoff/adapters/persistence/sqlite/ledger.py",
    "src/handsoff/adapters/memory/noop.py",
    "scenarios/nominal_arrival.yaml",
    "scenarios/false_proximity.yaml",
    "scenarios/blocked_garage.yaml",
    "scenarios/demand_response.yaml",
    "scenarios/stale_telemetry.yaml",
    "scenarios/partial_failure.yaml",
    "tests/test_foundation.py",
    "tests/contract/test_reference_scenarios.py",
    "tests/property/test_contract_properties.py",
    "tests/integration/test_runtime.py",
    "tests/scenarios/test_reference_runtime.py",
    "tests/unit/adapters/test_deterministic_clock.py",
    "tests/unit/domain/test_capabilities.py",
    "tests/unit/domain/test_events.py",
    "tests/unit/domain/test_execution.py",
    "tests/unit/domain/test_goals.py",
    "tests/unit/domain/test_observations.py",
    "tests/unit/domain/test_plans.py",
    "tests/unit/domain/test_policies.py",
    "tests/unit/domain/test_scenarios.py",
    "scripts/check_docs.py",
    "scripts/check_repository.py",
    "scripts/check_secrets.py",
    "scripts/validate.py",
    "scripts/run_demo.py",
    "scripts/evaluate_planner.py",
    "docs/streamlit-deployment.md",
    "docs/adr/0004-streamlit-hackathon-interface.md",
)
DEFERRED_MILESTONE_4_PATHS = (
    "streamlit_app.py",
    "src/handsoff/presentation",
    "src/handsoff/api",
    "src/handsoff/config.py",
    "web",
    ".streamlit/config.toml",
    "requirements.txt",
)
IGNORED_SENSITIVE_PATHS = (
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
    ".streamlit/secrets.toml",
    "runtime/state.sqlite3",
    "logs/handsoff.log",
)


def git_output(*args: str) -> str:
    """Return stripped Git output for a read-only repository query."""
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate_placeholder_environment(errors: list[str]) -> None:
    """Ensure the example environment file contains no assigned values."""
    example = ROOT / ".env.example"
    if not example.is_file():
        return
    for number, line in enumerate(example.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped or stripped.split("=", maxsplit=1)[1]:
            errors.append(f".env.example line {number} is not an empty placeholder")


def validate_sensitive_ignores(errors: list[str]) -> None:
    """Verify representative credential and runtime paths are ignored."""
    for path in IGNORED_SENSITIVE_PATHS:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"sensitive or runtime path is not ignored: {path}")


def validate_project_version(errors: list[str]) -> None:
    """Require package metadata to identify the completed planner milestone."""
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)
    if project.get("project", {}).get("version") != EXPECTED_VERSION:
        errors.append(f"project version must be {EXPECTED_VERSION} for Milestone 3")


def main() -> int:
    """Run Milestone 3 structural checks."""
    errors: list[str] = []

    errors.extend(
        f"missing required file: {relative_path}"
        for relative_path in REQUIRED_FILES
        if not (ROOT / relative_path).is_file()
    )

    if (ROOT / "LICENSE").exists():
        errors.append("LICENSE exists even though the license decision is pending")

    errors.extend(
        f"Milestone 4 interface path exists early: {relative_path}"
        for relative_path in DEFERRED_MILESTONE_4_PATHS
        if (ROOT / relative_path).exists()
    )

    if (ROOT / ".python-version").read_text(encoding="utf-8").strip() != "3.12":
        errors.append(".python-version must contain exactly 3.12")

    if sys.version_info[:2] != (3, 12):
        errors.append(f"validation requires Python 3.12, found {sys.version.split()[0]}")

    if git_output("branch", "--show-current") != "main":
        errors.append("repository branch is not main")

    validate_project_version(errors)
    validate_placeholder_environment(errors)
    validate_sensitive_ignores(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Repository validation passed (Milestone 3 boundaries preserved).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
