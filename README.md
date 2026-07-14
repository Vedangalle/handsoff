# Handsoff

**Internal description:** Physical Codex

**Product line:** Autonomy for ordinary life.

Handsoff is the working title for a local-first, vendor-independent goal-to-verified-outcome runtime. A user objective is compiled into an inspectable typed plan, evaluated by deterministic policy, executed only through constrained capabilities, and verified against observed world state.

This repository is at **Milestone 0: repository foundation**. It contains no deterministic runtime, domain models, API, simulator, external-provider adapters, Home Assistant integration, scenarios, or user interface. It is not production-ready and performs no real actuation.

## Core boundaries

- The model is a planner, not a controller.
- Model output and external telemetry are untrusted inputs.
- Deterministic policy is the authority boundary.
- Command acceptance and verified physical effect are distinct states.
- The operational core remains local by default; external calls cross an explicit privacy boundary.
- Simulation is required before shadow, supervised, or live-bounded operation.
- R3 safety-critical actions are prohibited in the prototype.

The approved architecture and all ten fixed decisions are recorded in [Architecture](docs/architecture.md).

## Documentation

- [Product charter](docs/product-charter.md)
- [Architecture](docs/architecture.md)
- [Privacy boundaries](docs/privacy-boundaries.md)
- [Threat model](docs/threat-model.md)
- [Verification plan](docs/verification-plan.md)
- [ADR 0001: Modular monolith](docs/adr/0001-modular-monolith.md)
- [ADR 0002: Model is not controller](docs/adr/0002-model-is-not-controller.md)
- [ADR 0003: Simulator first](docs/adr/0003-simulator-first.md)

## Prerequisites and installation

- Python 3.12
- `uv` 0.11 or later
- Git

Create the exact locked environment, including the optional Gemini planner boundary used by dependency validation:

```bash
uv sync --frozen --all-extras
```

The deterministic core must eventually install and operate without optional provider extras. No credential is needed for Milestone 0.

## Validation commands

Run individual gates from the repository root:

```bash
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src scripts tests
uv run --frozen coverage run -m pytest
uv run --frozen coverage report
uv lock --check
uv run --frozen --all-extras pip-audit --local --cache-dir .cache/pip-audit
uv run --frozen python scripts/check_secrets.py
uv run --frozen python scripts/check_docs.py
uv run --frozen python scripts/check_repository.py
git diff --check
```

Run the CI-equivalent local suite after syncing all optional dependencies:

```bash
uv run --frozen --all-extras python scripts/validate.py
```

The documentation check validates required documents, relative links, and Mermaid fence structure. It does not replace visual review in a Mermaid renderer. The secret scan enumerates only tracked and untracked non-ignored files and suppresses candidate values from output; it does not read ignored credential files.

## Repository scope

The target repository layout is defined in [Architecture](docs/architecture.md). Milestone directories are added only when their implementation is authorized. Runtime-generated databases, logs, evidence artifacts, credentials, and household data must remain outside version control.

## License

The software license is pending an explicit owner decision. No `LICENSE` file or package license metadata is present, and no permission to use, copy, modify, or distribute this work should be inferred.

## Naming

`Handsoff` is a hackathon working title, not a cleared commercial identity. Trademark, company-name, package-name, repository-name, handle, and domain clearance remain future work.
