"""Timestamped world-observation contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, JsonValue

from handsoff.domain import ContractModel, Identifier, NonEmptyText, UtcDateTime


class ObservationQuality(StrEnum):
    """Qualitative source assessment supplied with an observation."""

    NOMINAL = "nominal"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class Observation(ContractModel):
    """A normalized world-state value with provenance and freshness metadata."""

    observation_id: Identifier
    entity_id: Identifier
    property_id: Identifier
    value: JsonValue
    unit: NonEmptyText | None = None
    source_adapter_id: Identifier
    observed_at: UtcDateTime
    freshness_limit_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    quality: ObservationQuality
    correlation_id: Identifier | None = None


__all__ = ["Observation", "ObservationQuality"]
