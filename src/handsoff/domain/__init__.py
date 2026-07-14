"""Shared primitives for strict Handsoff domain contracts."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
    ),
]
ContractVersion = Annotated[
    str,
    StringConstraints(
        min_length=5,
        max_length=32,
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    ),
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _require_utc(value: AwareDatetime) -> AwareDatetime:
    """Reject aware timestamps that are not expressed in UTC."""
    if value.utcoffset() != timedelta(0):
        message = "timestamp must use UTC"
        raise ValueError(message)
    return value


UtcDateTime = Annotated[AwareDatetime, AfterValidator(_require_utc)]


class ContractModel(BaseModel):
    """Immutable, strict base class for data crossing a Handsoff boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )


__all__ = [
    "ContractModel",
    "ContractVersion",
    "Identifier",
    "NonEmptyText",
    "UtcDateTime",
]
