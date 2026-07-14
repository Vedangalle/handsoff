"""Run the CI-equivalent local Milestone 1 validation suite."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    ("Format", ("ruff", "format", "--check", ".")),
    ("Lint", ("ruff", "check", ".")),
    ("Static typing", ("mypy", "src", "scripts", "tests")),
    ("Tests", ("coverage", "run", "-m", "pytest")),
    ("Coverage", ("coverage", "report")),
    ("Lock consistency", ("uv", "lock", "--check")),
    ("Dependency audit", ("pip-audit", "--local", "--cache-dir", ".cache/pip-audit")),
    ("Secret scan", ("python", "scripts/check_secrets.py")),
    ("Documentation", ("python", "scripts/check_docs.py")),
    ("Repository", ("python", "scripts/check_repository.py")),
    ("Whitespace", ("git", "diff", "--check")),
)


def main() -> int:
    """Run every gate, stopping at the first failure."""
    if shutil.which("uv") is None:
        print("ERROR: uv is required on PATH for lock consistency validation.")
        return 1

    for label, command in COMMANDS:
        print(f"\n==> {label}: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            print(f"ERROR: {label} failed with exit code {result.returncode}.")
            return result.returncode

    print("\nAll Milestone 1 validation gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
