# ADR 0001: Modular Monolith with Hexagonal Boundaries

- **Status:** Accepted
- **Decision date:** 2026-07-13
- **Scope:** Prototype architecture

## Context

Handsoff must coordinate planning, deterministic policy, capability execution, verification, and evidence without allowing provider or infrastructure code to control domain behavior. The hackathon requires low operational complexity and clear future extraction points, not independent scaling of services.

## Decision

Implement one Python 3.12 deployable process as a modular monolith with hexagonal boundaries. Domain logic remains independent of FastAPI, databases, model SDKs, device providers, and user-interface code. Application services depend on ports; adapters implement external behavior. One process owns the execution state machine.

## Consequences

- Local transactions and deterministic tests remain straightforward.
- Deployment and failure modes are smaller than a distributed design.
- Boundary discipline must be enforced through imports, tests, and review rather than network separation.
- A bounded context may be extracted only when measured scale or reliability requirements justify the added distributed-systems cost.

## Rejected alternatives

- **Microservices:** premature operational and consistency complexity.
- **General agent framework:** unnecessary for one constrained typed planner call and incompatible with the deterministic authority boundary.
- **Event-source the entire application:** the append-only operational ledger is required, but full event sourcing is not justified for the prototype.
