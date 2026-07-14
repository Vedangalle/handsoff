# Handsoff Repository Working Agreement

This file supplements Vedang Alle's global working agreement for this repository. Task-specific instructions from Vedang take precedence.

## Engineering standard

- Optimize for technical correctness, reproducibility, safety, maintainability, documentation, and publication-quality evidence.
- State assumptions and uncertainty. Never invent behavior, results, measurements, benchmarks, or citations.
- Keep measured, observed, estimated, assumed, simulated, and predicted findings distinct.
- Use concise, precise technical language. Avoid marketing claims and unsupported statements.

## Architecture constraints

- Preserve the approved local-first modular monolith and hexagonal boundaries documented in `docs/architecture.md`.
- Keep domain logic independent of FastAPI, persistence, model SDKs, Home Assistant, Supermemory, and user-interface code.
- Treat model output and external telemetry as untrusted input.
- Never create a model-to-actuator path. Deterministic policy remains the authority boundary.
- Keep Gemini, Supermemory, Home Assistant, and other providers replaceable and outside the deterministic critical path.
- Maintain explicit simulation, shadow, supervised, and live-bounded modes. Never infer autonomy mode from provider availability.
- Do not add real actuation during the prototype. R3 actions remain prohibited.
- Do not add a `utils.py` dumping ground, pass database models through API routes, or place device-specific logic in domain or application packages.

## Change workflow

Before implementation, inspect the relevant architecture, dependencies, data flow, tests, and user changes. Propose a scoped change set and verification plan, then obtain approval unless Vedang explicitly authorized implementation.

During implementation:

- preserve unrelated changes;
- minimize breaking changes and unnecessary renames;
- keep credentials, real household data, runtime databases, logs, prompts, screenshots, and generated artifacts out of version control;
- update documentation when behavior or boundaries change; and
- add verification proportional to risk.

Review work must separate confirmed defects from risks, uncertainties, preferences, and optional improvements. Do not implement review findings unless requested.

## Validation and evidence

Run the complete validation command documented in `README.md` before handoff. Report the exact commands, results, branch, diff scope, and Git status. Do not commit, push, branch, or open a pull request unless Vedang explicitly requests it.

## License and credentials

No software license has been selected. Do not add license text or package license metadata without Vedang's explicit decision.

Never create, read, print, log, test with, or commit real credentials. `.env.example` may contain names and empty placeholders only.
