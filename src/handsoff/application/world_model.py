"""In-memory normalized world state with deterministic observation ordering."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsoff.domain.observations import Observation


class WorldModel:
    """Store immutable observations and expose the newest value per property."""

    def __init__(self, observations: tuple[Observation, ...] = ()) -> None:
        """Record an optional deterministic initial snapshot."""
        self._by_id: dict[str, Observation] = {}
        self._by_property: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        for observation in observations:
            self.record(observation)

    def record(self, observation: Observation) -> bool:
        """Record a new observation; identical duplicates are idempotent."""
        existing = self._by_id.get(observation.observation_id)
        if existing is not None:
            if existing != observation:
                message = "observation identifier already contains different evidence"
                raise ValueError(message)
            return False

        self._by_id[observation.observation_id] = observation
        key = (observation.entity_id, observation.property_id)
        self._by_property[key].append(observation)
        self._by_property[key].sort(
            key=lambda item: (item.observed_at, item.observation_id),
            reverse=True,
        )
        return True

    def latest(self, entity_id: str, property_id: str) -> Observation | None:
        """Return the newest observation for an entity property."""
        observations = self._by_property.get((entity_id, property_id), ())
        return observations[0] if observations else None

    def get(self, observation_id: str) -> Observation | None:
        """Return one observation by immutable identifier."""
        return self._by_id.get(observation_id)

    def observations(self) -> tuple[Observation, ...]:
        """Return all evidence in deterministic identifier order."""
        return tuple(self._by_id[key] for key in sorted(self._by_id))


__all__ = ["WorldModel"]
