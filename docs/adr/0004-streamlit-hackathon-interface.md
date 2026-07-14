# ADR 0004: Streamlit Hackathon Interface

- **Status:** Accepted
- **Date:** 2026-07-13
- **Decision owner:** Vedang Alle
- **Supersedes:** The FastAPI-specific portion of architecture decision 9

## Context

The original interface decision selected a thin FastAPI boundary. The hackathon now requires one publicly accessible, visually inspectable application that can demonstrate deterministic execution, optional Gemini planning, and optional Supermemory context without introducing a second deployed service.

Streamlit Community Cloud runs a repository entrypoint directly, supports Python 3.12, and provides application-level secret configuration. Deploying a separate API process would add hosting, networking, health, and cross-origin failure modes without improving the deterministic authority boundary.

## Decision

Use Streamlit as the Milestone 4 operator interface and public hackathon deployment surface.

- The Streamlit layer may call a typed application facade inside the same modular-monolith process.
- It contains presentation and session-state logic only; domain, policy, execution, verification, persistence, and provider behavior remain below ports.
- Every browser session receives isolated simulation state and an isolated evidence ledger.
- Gemini and Supermemory remain optional adapters. Missing credentials select deterministic planner and no-op memory behavior.
- Supermemory contributes bounded, visibly labeled, untrusted preference context to planning only.
- The public deployment uses a fixed demo-only, read-only Supermemory scope. Browser input cannot select arbitrary container tags or write shared memory.
- FastAPI is no longer required for the hackathon interface. A typed HTTP adapter may be added later only if an independently deployed client creates a measured need.

The first eight architecture decisions and decision 10 remain unchanged.

## Consequences

- Milestone 4 is the final hackathon milestone and includes the optional Supermemory comparison previously listed separately.
- The UI can be hosted as one process with fewer deployment failure modes.
- Streamlit reruns require explicit construction and caching boundaries; no mutable runtime singleton may be shared across user sessions.
- Community Cloud storage is not treated as durable operational persistence. The public demo replays synthetic fixtures and may export a session trace; production persistence is outside scope.
- Provider secrets are configured in Streamlit's secret manager and must never be committed, displayed, logged, cached as data, or included in prompts.

## Rejected alternatives

- **Streamlit plus a separately hosted FastAPI service:** unnecessary distributed-system complexity for the prototype.
- **Model or memory calls directly from UI widgets:** violates the adapter boundary and makes provider output harder to contain and test.
- **Public writable Supermemory scope:** creates cross-user contamination, privacy, abuse, and demonstration-reproducibility risks.
- **Supermemory as execution state:** violates provider independence and would place an external service in the authority path.
