"""Validate Milestone 0 repository invariants without reading credential files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    "tests/test_foundation.py",
    "scripts/check_docs.py",
    "scripts/check_repository.py",
    "scripts/check_secrets.py",
    "scripts/validate.py",
)
DEFERRED_RUNTIME_PATHS = (
    "src/handsoff/domain",
    "src/handsoff/application",
    "src/handsoff/ports",
    "src/handsoff/adapters",
    "src/handsoff/api",
    "src/handsoff/config.py",
    "scenarios",
    "web",
    "scripts/run_demo.py",
)
IGNORED_SENSITIVE_PATHS = (
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
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


def main() -> int:
    """Run Milestone 0 structural checks."""
    errors: list[str] = []

    errors.extend(
        f"missing required file: {relative_path}"
        for relative_path in REQUIRED_FILES
        if not (ROOT / relative_path).is_file()
    )

    if (ROOT / "LICENSE").exists():
        errors.append("LICENSE exists even though the license decision is pending")

    errors.extend(
        f"post-Milestone 0 runtime path exists: {relative_path}"
        for relative_path in DEFERRED_RUNTIME_PATHS
        if (ROOT / relative_path).exists()
    )

    if (ROOT / ".python-version").read_text(encoding="utf-8").strip() != "3.12":
        errors.append(".python-version must contain exactly 3.12")

    if sys.version_info[:2] != (3, 12):
        errors.append(f"validation requires Python 3.12, found {sys.version.split()[0]}")

    if git_output("branch", "--show-current") != "main":
        errors.append("initial branch is not main")

    validate_placeholder_environment(errors)
    validate_sensitive_ignores(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Repository validation passed (Milestone 0 boundaries preserved).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
