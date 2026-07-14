# ADR 0002: The Model Is Not the Controller

- **Status:** Accepted
- **Decision date:** 2026-07-13
- **Scope:** Planning, authority, and execution boundary

## Context

Natural-language objectives require interpretation, but model output is probabilistic, externally processed, and vulnerable to malformed output and prompt injection. Physical action requires deterministic authority, bounded capabilities, fresh state, and reproducible evidence.

## Decision

Gemini may propose a typed `PlanProposal` through an adapter. Its output is untrusted data subject to strict schema validation and deterministic policy. The model cannot call a device adapter, grant approval, alter policy, select autonomy mode, verify an outcome, or write authoritative execution state.

The deterministic core must function with a fixture planner when Gemini is disabled or unavailable. Supermemory, if later added, provides optional context only and cannot participate in authority, execution, or verification.

## Consequences

- Planner quality and deterministic runtime correctness can be measured separately.
- Invalid, unavailable, or compromised model output fails without side effects.
- Capabilities, policy, and acceptance conditions require explicit typed contracts.
- More deterministic application logic is required than in an agent-controlled design.

## Rejected alternatives

- **Model tool-calling directly into devices:** creates an unauthorized model-to-actuator path.
- **Natural-language policy evaluation:** cannot provide the required deterministic, versioned decision evidence.
- **Model-based outcome verification:** repeats planner uncertainty and cannot replace fresh explicit telemetry checks.
