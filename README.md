<h1 align="center">Handsoff</h1>

<p align="center"><strong>Autonomy for ordinary life.</strong></p>

<p align="center"><strong>A local-first, vendor-independent runtime for turning human goals into policy-checked actions and verified real-world outcomes.</strong></p>

<p align="center">
  <img alt="Project status: Milestone 4 complete" src="https://img.shields.io/badge/status-Milestone%204%20complete-1f6feb">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&amp;logoColor=white">
  <img alt="Dependencies locked with uv" src="https://img.shields.io/badge/dependencies-uv%20locked-6f42c1">
  <img alt="Actuation: none" src="https://img.shields.io/badge/real%20actuation-none-d73a49">
  <img alt="License pending" src="https://img.shields.io/badge/license-pending-lightgrey">
</p>

<p align="center"><em>Internal prototype description: Physical Codex</em></p>

> [!IMPORTANT]
> Handsoff has completed **Milestone 4: the hackathon application**. The repository contains the deterministic simulation core, six reference scenarios, append-only evidence, contained Gemini planning with offline fallback, bounded read-only Supermemory context, and an inspectable Streamlit operator surface. This repository does not control real devices.

## The idea

Most consumer automation begins with commands:

> If this event occurs, send this instruction to that device.

Handsoff begins with an outcome:

> Prepare my environment for arrival in five minutes.

The system is designed to compile that objective into an inspectable typed plan, evaluate every proposed action with deterministic policy, execute only allowlisted capabilities, and verify the resulting world state from fresh telemetry. A successful API response is not treated as proof that a physical effect occurred.

The model can propose a plan. It can never grant itself authority to act.

## Why this architecture exists

| Conventional automation | Handsoff target architecture |
|---|---|
| Device commands and trigger chains | Goals with explicit acceptance conditions |
| Vendor-specific orchestration | Typed, replaceable capability adapters |
| API success treated as completion | Independent telemetry-based outcome verification |
| Implicit or scattered authority | Deterministic, versioned policy decisions |
| Best-effort handling of stale state | Timestamp, freshness, confidence, and contradiction checks |
| Partial failure hidden behind a success path | Explicit partial-success, failure, timeout, and compensation states |
| Cloud provider as the control plane | Local policy, execution state, and operational ledger |

Handsoff is not intended to replace Matter, Home Assistant, device firmware, or vendor APIs. It is a user-owned coordination and verification layer above bounded integrations.

## Contents

- [The idea](#the-idea)
- [Why this architecture exists](#why-this-architecture-exists)
- [System model](#system-model)
- [Safety invariants](#safety-invariants)
- [Canonical demonstration](#canonical-demonstration)
- [Current implementation status](#current-implementation-status)
- [Autonomy modes](#autonomy-modes)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Validation](#validation)
- [Dependency strategy](#dependency-strategy)
- [Streamlit and Supermemory path](#streamlit-and-supermemory-path)
- [Roadmap](#roadmap)
- [Engineering documentation](#engineering-documentation)
- [Security and privacy](#security-and-privacy)
- [Engineering standard](#engineering-standard)
- [License and naming](#license-and-naming)

## System model

Handsoff uses a **modular monolith with hexagonal boundaries**. Domain logic remains independent of web frameworks, databases, model SDKs, device providers, and user-interface code. External systems attach through explicit ports and constrained adapters.

```mermaid
flowchart LR
    GOAL["Human objective"] --> GC["Goal compiler"]
    STATE["Timestamped world state"] --> GC
    CAPS["Capability registry"] --> GC
    MODEL["Optional model planner"] -. "typed proposal only" .-> GC
    MEMORY["Optional preference memory"] -. "context only" .-> GC

    GC --> PLAN["Untrusted plan proposal"]
    PLAN --> SCHEMA["Strict schema validation"]
    SCHEMA --> POLICY["Deterministic policy kernel"]

    POLICY -->|deny| LEDGER["Append-only evidence ledger"]
    POLICY -->|approval required| USER["Human approval boundary"]
    USER --> POLICY
    POLICY -->|allow| EXEC["Execution state machine"]

    EXEC --> ADAPTERS["Bounded capability adapters"]
    ADAPTERS --> TELEMETRY["Observed telemetry"]
    TELEMETRY --> VERIFY["Outcome verifier"]
    VERIFY --> LEDGER
    VERIFY --> STATE
```

### Authority and evidence boundaries

| Component | May propose | May authorize | May execute | May verify |
|---|---:|---:|---:|---:|
| User | Yes | Through explicit approval | No direct runtime bypass | Defines acceptance conditions |
| Gemini planner adapter | Yes | No | No | No |
| Optional semantic memory | Context only | No | No | No |
| Deterministic policy kernel | No | Yes | No | No |
| Execution state machine | No | Enforces prior decision | Through bounded adapters | No |
| Outcome verifier | No | No | No | Yes, from explicit conditions and observations |

See [Architecture](docs/architecture.md) for the fixed architectural decisions, target bounded contexts, trust boundary, and structural constraints.

## Safety invariants

These are executable simulation invariants. Milestones 2 and 3 implement and test their runtime and planner boundaries.

1. **No model-to-actuator path.** Model output is untrusted proposed data.
2. **Least authority.** Every adapter exposes typed, versioned, allowlisted capabilities.
3. **Fail closed.** Ambiguity, stale telemetry, invalid schemas, policy failure, or unavailable verification prevents actuation.
4. **State is time-bounded.** Observations require timestamps, freshness limits, source identity, and quality indicators.
5. **Acceptance is not verification.** An adapter accepting a command does not prove the intended effect occurred.
6. **Duplicate effects are bounded.** Commands require idempotency behavior and duplicate-action prevention.
7. **Autonomy mode is explicit.** Runtime mode is configured and recorded, never inferred from provider availability.
8. **R3 actions are prohibited.** Safety-critical, vehicle-motion, life-support, fire, gas, high-energy, and security-critical actions cannot execute in the prototype.
9. **Evidence precedes claims.** Plans, policy decisions, approvals, transitions, observations, and verification results require an inspectable trace.
10. **Providers remain replaceable.** Gemini, Supermemory, Home Assistant, and other vendors remain outside the deterministic critical path.

The full adversary model, required controls, residual risks, and risk classes are documented in the [Threat model](docs/threat-model.md).

## Canonical demonstration

The first target scenario is:

> **Prepare my environment for arrival in five minutes.**

The deterministic simulator coordinates destination confidence, garage state, charger readiness, room conditioning, media readiness, and energy constraints.

The architecture is not demonstrated by a single happy path. The approved scenario suite must cover:

| Scenario | Required behavior |
|---|---|
| Nominal arrival | All permitted actions complete and every acceptance condition is verified |
| False proximity | No arrival actions execute when destination confidence is insufficient |
| Blocked garage | The garage action is withheld while obstruction telemetry is active |
| Demand response | Energy policy produces a bounded alternative rather than an unsafe override |
| Stale telemetry | Required stale observations block execution |
| Partial failure | The trace reports partial success, failure, or compensation—never false success |
| Malicious external text | Untrusted content cannot create an undeclared capability |

All six named fixtures are committed, schema-validated, executed through the deterministic runtime, and compared against policy, dispatch, terminal-state, and verification expectations.

## Current implementation status

| Area | Status | Evidence in this repository |
|---|---|---|
| Git and Python foundation | Implemented | Python 3.12 project metadata, package boundary, and locked dependency graph |
| Engineering documentation | Implemented | Product charter, architecture, privacy boundaries, threat model, verification plan, and ADRs |
| Repository quality gates | Implemented | Formatting, linting, strict typing, tests, coverage, audit, secret, docs, and repository checks |
| Strict domain contracts | Implemented | Goals, observations, capabilities, plans, policy results, approvals, transitions, events, verification, and scenarios |
| Policy and transition invariants | Implemented at contract layer | Contradictory policy results, R3 authorization, illegal state transitions, cycles, and undeclared references are rejected |
| Deterministic test clock | Implemented | UTC-only monotonic clock behind a clock port |
| Reference scenario fixtures | Implemented | Six self-contained simulation-only YAML fixtures with deterministic expected outcomes |
| Deterministic runtime and simulator | Implemented | World model, registry, policy kernel, approval binding, state machine, verifier, retries, duplicate suppression, and six executable scenarios |
| Operational ledger | Implemented | Ordered append-only in-memory and transactional SQLite repositories |
| Gemini planner adapter | Implemented and optional | Minimized prompt, Pydantic structured output, trusted binding checks, no tools, deterministic fallback |
| Planner evaluation | Implemented | Configuration, schema validity, hallucinations, parameters, preconditions, policy result, latency, and token usage |
| Memory boundary | Implemented and optional | Context-only port, no-op and synthetic adapters, read-only Supermemory search, fixed scope, five-result limit, normalization, and fail-closed fallback |
| Operator interface | Implemented | Original responsive Streamlit mission control with narrative outcome, proposal, policy, transitions, verification, ledger, and memory evidence views |
| Supermemory demonstration | Implemented and optional | Hybrid retrieval supplies bounded untrusted planner context; no writes or authority path exist |
| Home Assistant integration | Post-hackathon | Not part of the M4 completion line |
| Real device actuation | Prohibited | No real actuation in the prototype |

The package version is `0.4.0`. The deterministic CLI, planner-evaluation runner, and Streamlit operator application are supported hackathon workflows.

## Autonomy modes

| Mode | State source | Planning | Execution | Status |
|---|---|---|---|---|
| Simulation | Deterministic simulated state | Yes | Simulated actions only | **Implemented** |
| Shadow | Live read-only state | Yes | None | Architecture-ready; optional demonstration |
| Supervised | Live state | Yes | Only after explicit approval | Post-prototype |
| Live bounded | Live state | Yes | Allowlisted low-risk actions | Post-security review |

No mode performs real actuation. Shadow, supervised, and live-bounded modes remain post-hackathon work.

## Repository structure

The repository now contains the complete hackathon application:

```text
handsoff/
├── AGENTS.md                       # Repository engineering agreement
├── README.md                       # Project entry point
├── pyproject.toml                  # Python project and quality-tool configuration
├── uv.lock                         # Exact dependency resolution
├── .python-version                 # Python 3.12 baseline
├── .env.example                    # Empty configuration placeholders only
├── streamlit_app.py                # Public operator entrypoint
├── requirements.txt                # Community Cloud project extras
├── .streamlit/config.toml          # Non-secret presentation configuration
├── docs/
│   ├── product-charter.md
│   ├── architecture.md
│   ├── privacy-boundaries.md
│   ├── threat-model.md
│   ├── verification-plan.md
│   ├── streamlit-deployment.md
│   └── adr/
│       ├── 0001-modular-monolith.md
│       ├── 0002-model-is-not-controller.md
│       ├── 0003-simulator-first.md
│       └── 0004-streamlit-hackathon-interface.md
├── scripts/
│   ├── check_docs.py
│   ├── check_repository.py
│   ├── check_secrets.py
│   ├── evaluate_planner.py
│   ├── run_demo.py
│   └── validate.py
├── src/handsoff/
│   ├── adapters/
│   │   ├── clock/                  # Deterministic test time
│   │   ├── devices/simulator/      # Scripted effects; no real devices
│   │   ├── memory/                 # No-op, synthetic, Supermemory, and fail-closed adapters
│   │   ├── persistence/            # In-memory and SQLite ledgers
│   │   └── planner/                # Fixture, Gemini, and fallback planners
│   ├── application/                # Policy, execution, verification, scenarios
│   ├── domain/
│   │   ├── capabilities.py
│   │   ├── events.py
│   │   ├── execution.py
│   │   ├── goals.py
│   │   ├── observations.py
│   │   ├── planning.py
│   │   ├── plans.py
│   │   ├── policies.py
│   │   └── scenarios.py
│   ├── ports/                      # Planner, memory, adapter, ledger, and clock
│   ├── presentation/               # Typed facade, configuration, and session state
│   ├── __init__.py
│   └── py.typed
├── scenarios/
│   ├── blocked_garage.yaml
│   ├── demand_response.yaml
│   ├── false_proximity.yaml
│   ├── nominal_arrival.yaml
│   ├── partial_failure.yaml
│   └── stale_telemetry.yaml
└── tests/
    ├── contract/
    ├── fixtures/
    ├── integration/
    ├── property/
    ├── scenarios/
    ├── unit/
    └── test_foundation.py
```

The Streamlit composition and deployment boundary are specified in the [deployment guide](docs/streamlit-deployment.md).

## Getting started

### Prerequisites

- Git
- [`uv`](https://docs.astral.sh/uv/) 0.11 or later
- Python 3.12; `uv` can provision the interpreter if it is not already installed

### Clone and reproduce the environment

```bash
git clone https://github.com/Vedangalle/handsoff.git
cd handsoff
uv python install 3.12
uv sync --frozen
```

This installs the project and default development dependency group exactly from `uv.lock`.

To reproduce the environment used by the complete validation suite, including the optional Gemini planner dependency boundary:

```bash
uv sync --frozen --all-extras
```

No credential is required for deterministic execution, replay, evaluation, or validation. `.env.example` contains names and empty values only. Do not add real credentials to fixtures, prompts, logs, screenshots, tests, or version control.

### Run the deterministic demonstration

```bash
uv run --frozen python scripts/run_demo.py
```

This executes all six fixtures and reports measured policy decision, terminal state, and ledger-event count. It performs no network call and requires no credential.

### Run the offline planner evaluation

```bash
uv run --frozen python scripts/evaluate_planner.py
```

This emits JSON Lines evaluation records for the deterministic baseline. Live Gemini evaluation is intentionally opt-in and is never part of repository validation.

### Run the Streamlit application

Install the application and optional Gemini extra, then launch the operator surface:

```bash
uv sync --frozen --all-extras
uv run --frozen --all-extras streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit. The default **Offline memory lab** is the complete, presentation-ready path: it requires no credential, makes no network call, and supplies clearly labeled synthetic preference records through the same bounded memory port. Select any committed mission and inspect the goal-to-evidence pipeline, typed proposal, policy reasons, state transitions, outcome verification, ordered ledger, and memory trust boundary.

The synthetic mode is deliberately honest about what it proves. It demonstrates context retrieval, normalization, planner containment, and the authority boundary; it does not claim that a live Supermemory request occurred. Deterministic baseline also remains fully offline. Live Gemini and Supermemory modes are optional comparisons for deployments with newly issued server-side credentials.

Optional local provider configuration belongs in ignored `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = ""
SUPERMEMORY_API_KEY = ""
HANDSOFF_MEMORY_SCOPE = "handsoff-public-demo-v1"
```

Never commit that file. The browser cannot choose provider endpoints, model identifiers, or Supermemory container tags. Missing or invalid providers fall back visibly to deterministic planning or empty memory context without weakening policy.

## Validation

Run the complete CI-equivalent local gate:

```bash
uv run --frozen --all-extras python scripts/validate.py
```

The aggregate command stops at the first failure and executes:

| Gate | Command | What it establishes |
|---|---|---|
| Format | `ruff format --check .` | Python formatting matches the repository configuration |
| Lint | `ruff check .` | Configured Ruff rules pass |
| Static typing | `mypy src scripts tests streamlit_app.py` | Strict Python 3.12 analysis passes |
| Tests | `coverage run -m pytest` | The current test suite passes under strict pytest settings |
| Coverage | `coverage report` | Package branch coverage meets the configured threshold |
| Lock consistency | `uv lock --check` | `pyproject.toml` and `uv.lock` agree |
| Dependency audit | `pip-audit --local --cache-dir .cache/pip-audit` | Installed dependencies have no reported known vulnerabilities |
| Secret scan | `python scripts/check_secrets.py` | Git-visible files contain no detected secret candidates |
| Documentation | `python scripts/check_docs.py` | Required documents, relative links, and Mermaid fence structure pass |
| Repository boundary | `python scripts/check_repository.py` | Milestone, branch, placeholder, ignore, Python, and license invariants hold |
| Whitespace | `git diff --check` | The tracked diff has no whitespace errors |

The detailed evidence contract, known limitations of documentation validation, and future test hierarchy are in the [Verification plan](docs/verification-plan.md).

## Dependency strategy

The deterministic core must remain installable and testable without Gemini, Supermemory, or Home Assistant.

### Declared runtime foundation

- `pydantic` — strict schemas at trust boundaries
- `sqlalchemy` and `alembic` — local SQLite persistence boundary and migration tooling
- `httpx` — bounded external-adapter transport
- `pyyaml` — human-readable deterministic scenario fixtures

### Optional integration boundary

- `google-genai` is isolated in the `planner-gemini` extra. The adapter is implemented but never enabled implicitly.
- `streamlit==1.59.2` is pinned in the `app` extra. The Supermemory adapter uses the existing `httpx` boundary and adds no provider SDK to the deterministic core.
- No Home Assistant dependency has been selected.

## Streamlit and Supermemory path

Milestone 4 is a single-process Streamlit application over typed application services. It supports four visible modes: deterministic baseline, an offline synthetic-memory lab, optional Gemini planning, and optional Gemini plus read-only Supermemory context. The core and the complete visual demonstration remain functional when both external providers are disabled.

The public demo uses one fixed server-configured, demo-only Supermemory scope; retrieves at most five hybrid-search results; normalizes and truncates each result; labels it untrusted; and passes it only to planner context. Browser users cannot select container tags or write shared memory. Provider keys remain in Streamlit Community Cloud secrets, never in Git or session output.

The full process, session-isolation requirements, secret placeholders, packaging plan, and acceptance criteria are in [Streamlit and Supermemory deployment](docs/streamlit-deployment.md).

### Explicit exclusions

The prototype core does not use LangChain, a general agent framework, Celery, Redis, Kafka, Kubernetes, a vector database, an embedded policy DSL, or a direct Matter implementation. Additional infrastructure must be justified by measured requirements, not architectural fashion.

## Roadmap

| Milestone | Scope | State |
|---|---|---|
| **M0 — Repository foundation** | Git, Python project, lockfile, documentation, ADRs, and local quality gates | **Complete** |
| **M1 — Contracts and deterministic tests** | Domain vocabulary, strict schemas, test clock, scenario schema, six fixtures, and fail-first invariant tests | **Complete** |
| **M2 — Deterministic runtime** | World model, capability registry, policy kernel, state machine, verifier, ledger, simulator, and executable scenarios | **Complete** |
| **M3 — Contained planner** | Minimized Gemini structured output, trusted binding checks, deterministic fallback, optional memory port, and model evaluation | **Complete** |
| **M4 — Hackathon application** | Streamlit world/plan/policy/approval/timeline/replay UI plus optional read-only Supermemory context comparison | **Complete** |

Milestone 4 is the completed hackathon line. There are no additional committed milestones. Home Assistant shadow integration, live telemetry, and any real-device work are optional post-hackathon extensions requiring separate architecture and security approval.

## Engineering documentation

| Document | Purpose |
|---|---|
| [Product charter](docs/product-charter.md) | Mission, user, prototype wedge, principles, promise, and non-goals |
| [Architecture](docs/architecture.md) | Fixed decisions, data flow, trust boundary, bounded contexts, and target structure |
| [Privacy boundaries](docs/privacy-boundaries.md) | Data zones, credential handling, external-provider disclosure, and residual privacy risk |
| [Threat model](docs/threat-model.md) | Assets, adversaries, abuse paths, controls, risk classes, and residual risk |
| [Verification plan](docs/verification-plan.md) | Evidence standard, current gates, future test hierarchy, and prototype acceptance criteria |
| [Streamlit deployment](docs/streamlit-deployment.md) | M4 process, Supermemory boundary, session isolation, secrets, packaging, and acceptance |
| [ADR 0001](docs/adr/0001-modular-monolith.md) | Modular monolith with hexagonal boundaries |
| [ADR 0002](docs/adr/0002-model-is-not-controller.md) | Model planning without model authority |
| [ADR 0003](docs/adr/0003-simulator-first.md) | Deterministic simulation before live integration |
| [ADR 0004](docs/adr/0004-streamlit-hackathon-interface.md) | Streamlit hackathon surface and consolidation of the optional memory demo |
| [AGENTS.md](AGENTS.md) | Repository-specific engineering, review, security, and validation agreement |

Architecture decisions 1–10 were approved on 2026-07-13. Vedang explicitly revised the hackathon interface and completion line on the same date; ADR 0004 records the Streamlit decision and supersedes only the FastAPI-specific portion of decision 9.

## Security and privacy

Handsoff may eventually process data that reveals location, occupancy, routine, energy use, media context, device state, and action history. “Local-first” means the trusted operational core remains local by default; it does **not** mean configured external-provider calls remain on-device.

- Credentials belong in ignored local environment files or OS credential interfaces, never source control or model context.
- External-provider inputs must be minimized and documented.
- Optional memory cannot grant authority, change policy, execute actions, or verify outcomes.
- Evidence exports require review and redaction before leaving the local boundary.
- No real household data is required for the deterministic demonstration.

Report suspected security issues privately to the repository owner rather than publishing credential material or exploit details in an issue. No claim of production security, regulatory compliance, formal verification, penetration testing, or hardware-in-the-loop validation is made.

## Engineering standard

Changes are expected to preserve architectural boundaries, document assumptions, distinguish observed evidence from planned behavior, and include verification proportional to risk. Before proposing a commit, run the aggregate validation suite and inspect the exact diff and Git status.

Repository-specific instructions are defined in [AGENTS.md](AGENTS.md).

## License and naming

No software license has been selected. The absence of a license means permission to use, copy, modify, or distribute this work should not be inferred. A `LICENSE` file and package license metadata will be added only after an explicit owner decision.

`Handsoff` is a hackathon working title, not a cleared commercial identity. Trademark, company-name, package-name, repository-name, social-handle, and domain clearance remain future work.

---

<p align="center">
  <strong>Handsoff</strong> · Autonomy for ordinary life.<br>
  Maintained by <a href="https://github.com/Vedangalle">Vedang Alle</a>
</p>
