"""Scan only Git-visible repository files without exposing candidate values."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]


class Finding(TypedDict):
    """Non-sensitive fields emitted by detect-secrets."""

    line_number: int
    type: str


def git_visible_files() -> list[str]:
    """List tracked and untracked, non-ignored files without reading ignored files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode() for item in result.stdout.split(b"\0") if item]


def main() -> int:
    """Run detect-secrets against Git-visible files and redact candidate values."""
    files = git_visible_files()
    result = subprocess.run(
        ["detect-secrets", "scan", *files],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: detect-secrets failed; scanner output suppressed to protect values.")
        return result.returncode

    payload = cast("dict[str, object]", json.loads(result.stdout))
    raw_results = cast("dict[str, list[Finding]]", payload.get("results", {}))
    findings = [(path, finding) for path, items in raw_results.items() for finding in items]
    if findings:
        print("ERROR: potential secrets detected (candidate values suppressed):")
        for path, finding in findings:
            print(f"  {path}:{finding['line_number']} ({finding['type']})")
        return 1

    print(f"Secret scan passed ({len(files)} Git-visible files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
