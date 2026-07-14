# ADR 0003: Deterministic Simulator First

- **Status:** Accepted
- **Decision date:** 2026-07-13
- **Scope:** Integration sequence and prototype safety

## Context

The architecture must demonstrate goal compilation, policy, partial failure, verification, and evidence without risking people or property. Real devices introduce unavailable hardware, vendor behavior, broad credentials, nondeterministic state, and failure conditions that are difficult to reproduce.

## Decision

Implement a deterministic simulated world before any live integration. The prototype performs no real actuation, and R3 capabilities remain prohibited. The required scenarios are nominal arrival, false proximity, blocked garage, demand response, stale telemetry, and partial failure.

Home Assistant may be considered later as a read-only shadow integration. Supervised low-risk actions require a separate security review and explicit authorization. Live-bounded operation is post-prototype.

## Consequences

- Scenarios and failures can be reproduced without credentials or household data.
- Safety and policy invariants can be tested before provider-specific complexity.
- Simulation evidence cannot be represented as real-world safety or reliability evidence.
- Adapter contracts must preserve the distinction between command acceptance and independently observed effect.

## Rejected alternatives

- **Live integration first:** adds physical and credential risk before deterministic behavior is established.
- **Home Assistant as the domain model:** couples the core to one integration substrate.
- **Mock-only tests without a simulated world:** insufficient for stateful partial-failure and verification behavior.
