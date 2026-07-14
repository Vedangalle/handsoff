"""Validate required Markdown files, local links, and Mermaid fence structure."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "docs/product-charter.md",
    ROOT / "docs/architecture.md",
    ROOT / "docs/privacy-boundaries.md",
    ROOT / "docs/threat-model.md",
    ROOT / "docs/verification-plan.md",
    ROOT / "docs/streamlit-deployment.md",
    ROOT / "docs/adr/0001-modular-monolith.md",
    ROOT / "docs/adr/0002-model-is-not-controller.md",
    ROOT / "docs/adr/0003-simulator-first.md",
    ROOT / "docs/adr/0004-streamlit-hackathon-interface.md",
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
MERMAID_DECLARATIONS = ("flowchart ", "graph ", "sequenceDiagram", "stateDiagram")


def markdown_files() -> list[Path]:
    """Return repository Markdown files without reading ignored credential files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    relative_paths = (Path(item.decode()) for item in result.stdout.split(b"\0") if item)
    return sorted(ROOT / path for path in relative_paths if path.suffix == ".md")


def validate_required_documents(errors: list[str]) -> None:
    """Verify the approved documentation foundation exists and is non-empty."""
    for path in REQUIRED_DOCUMENTS:
        if not path.is_file():
            errors.append(f"missing required document: {path.relative_to(ROOT)}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty required document: {path.relative_to(ROOT)}")


def validate_local_links(path: Path, content: str, errors: list[str]) -> None:
    """Verify relative Markdown link targets exist."""
    for target in LINK_PATTERN.findall(content):
        clean_target = target.split("#", maxsplit=1)[0]
        if not clean_target or clean_target.startswith(("https://", "http://", "mailto:")):
            continue
        target_path = (path.parent / clean_target).resolve()
        if not target_path.exists():
            errors.append(f"broken local link in {path.relative_to(ROOT)}: {clean_target}")


def validate_mermaid(path: Path, content: str, errors: list[str]) -> None:
    """Verify Mermaid fences are closed, non-empty, and declare a diagram type."""
    opening_count = content.count("```mermaid")
    blocks = MERMAID_PATTERN.findall(content)
    if opening_count != len(blocks):
        errors.append(f"unclosed Mermaid fence in {path.relative_to(ROOT)}")
    for index, block in enumerate(blocks, start=1):
        diagram = block.strip()
        if not diagram:
            errors.append(f"empty Mermaid block {index} in {path.relative_to(ROOT)}")
        elif not diagram.startswith(MERMAID_DECLARATIONS):
            errors.append(
                f"unsupported Mermaid declaration in {path.relative_to(ROOT)} block {index}"
            )


def main() -> int:
    """Run documentation foundation checks."""
    errors: list[str] = []
    validate_required_documents(errors)
    for path in markdown_files():
        content = path.read_text(encoding="utf-8")
        validate_local_links(path, content, errors)
        validate_mermaid(path, content, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Documentation validation passed ({len(markdown_files())} Markdown files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
