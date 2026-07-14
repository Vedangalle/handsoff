"""Non-secret Milestone 4 application configuration contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from handsoff.adapters.planner.gemini import DEFAULT_MODEL

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_MEMORY_SCOPE = "handsoff-public-demo-v1"
_SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9_:-]{1,100}$")


@dataclass(frozen=True, slots=True)
class DemoSettings:
    """Server-controlled provider configuration; no browser value is accepted."""

    google_api_key: str | None = None
    supermemory_api_key: str | None = None
    memory_scope: str = DEFAULT_MEMORY_SCOPE
    gemini_model: str = DEFAULT_MODEL

    def __post_init__(self) -> None:
        """Reject unsafe scope and blank explicit model configuration."""
        if _SCOPE_PATTERN.fullmatch(self.memory_scope) is None:
            message = "memory scope must be a bounded container tag"
            raise ValueError(message)
        if not self.gemini_model.strip():
            message = "Gemini model cannot be blank"
            raise ValueError(message)

    @property
    def gemini_available(self) -> bool:
        """Report configuration presence without disclosing a value."""
        return bool(self.google_api_key)

    @property
    def supermemory_available(self) -> bool:
        """Report configuration presence without disclosing a value."""
        return bool(self.supermemory_api_key)

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> DemoSettings:
        """Read only allowlisted server-side keys and normalize empty placeholders."""

        def optional_text(key: str) -> str | None:
            value = values.get(key)
            if not isinstance(value, str):
                return None
            stripped = value.strip()
            return stripped or None

        return cls(
            google_api_key=optional_text("GOOGLE_API_KEY"),
            supermemory_api_key=optional_text("SUPERMEMORY_API_KEY"),
            memory_scope=optional_text("HANDSOFF_MEMORY_SCOPE") or DEFAULT_MEMORY_SCOPE,
            gemini_model=optional_text("HANDSOFF_GEMINI_MODEL") or DEFAULT_MODEL,
        )


__all__ = ["DEFAULT_MEMORY_SCOPE", "DemoSettings"]
