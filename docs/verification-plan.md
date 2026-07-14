# Verification Plan

## Evidence standard

Verification distinguishes requirements, implemented checks, observed results, and future acceptance criteria. Passing Milestone 4 validates the deterministic simulation runtime, contained provider boundaries, and Streamlit demonstration against synthetic fixtures; it is not evidence of real-device safety, production security, provider availability, or future model behavior.

## Milestone 4 gates

| Gate | Command | Evidence |
|---|---|---|
| Locked installation | `uv sync --frozen --all-extras` | Environment resolves exactly from `uv.lock` without modifying it |
| Formatting | `uv run --frozen ruff format --check .` | All supported source files match the configured formatter |
| Linting | `uv run --frozen ruff check .` | Configured Ruff rules report no defects |
| Static typing | `uv run --frozen mypy src scripts tests streamlit_app.py` | Strict Python 3.12 type analysis passes |
| Tests | `uv run --frozen coverage run -m pytest` | Unit, property, contract, integration, and scenario tests pass |
| Branch coverage | `uv run --frozen coverage report` | Package line and branch coverage meet the configured 100% threshold |
| Lock consistency | `uv lock --check` | Declarations and lockfile agree |
| Dependency audit | `uv run --frozen --all-extras pip-audit --local --cache-dir .cache/pip-audit` | Installed core, development, Gemini, and Streamlit dependencies have no reported known vulnerabilities |
| Secret scan | `uv run --frozen python scripts/check_secrets.py` | Git-visible files have no detected candidates; candidate values are never printed |
| Documentation | `uv run --frozen python scripts/check_docs.py` | Required files, local links, and Mermaid fence structure pass |
| Repository boundary | `uv run --frozen python scripts/check_repository.py` | Branch, Python baseline, ignored paths, placeholders, required M4 files, deployment packaging, pinned Streamlit, license state, and post-hackathon exclusions pass |
| Whitespace | `git diff --check` | No whitespace errors are present |

The aggregate command is:

```bash
uv run --frozen --all-extras python scripts/validate.py
```

Before handoff, inspect `git diff --stat`, `git diff --check`, all untracked files, the current branch, and `git status --short --branch`. No files are staged by default.

## Documentation validation limitation

The documentation script verifies relative targets and Mermaid fence structure. Mermaid diagrams must also be visually rendered and reviewed when a renderer becomes part of the documented toolchain. Structural validation is not a full Mermaid parser.

## Implemented evidence

The suite verifies:

- strict immutable models reject unknown fields and invalid coercions;
- timestamps are aware and explicitly UTC;
- observations enforce finite positive freshness and bounded confidence;
- capabilities enforce risk, authority, idempotency, evidence, compensation, and supported-mode rules;
- plans reject duplicate identifiers, undeclared dependencies, self-dependencies, and cycles;
- R3 policy results can only deny, and plan-level policy decisions must aggregate action results consistently;
- approval scopes are unique and time-bounded;
- every declared plan/action transition is accepted and every undeclared transition is rejected;
- ledger event kinds agree with their payload types;
- the deterministic clock cannot move backward;
- all six YAML fixtures validate, round-trip deterministically, and grant no live or R3 authority;
- scenario expectations cannot contradict or reference undeclared capabilities or conditions;
- condition evaluation fails closed on missing, future, stale, unknown-quality, zero-confidence, wrong-unit, and unsatisfied evidence;
- capability parameters, modes, versions, targets, risk, authority, approvals, expiration, preconditions, and destination confidence are checked before dispatch;
- adapter acceptance, observed effects, and verified outcomes remain distinct states;
- duplicate effects are suppressed, retries are bounded, and failed dependencies are not dispatched;
- in-memory and SQLite ledgers enforce unique event IDs and ordered stream sequences;
- all six committed scenarios match policy, dispatch, terminal-state, and verification expectations;
- Gemini input is minimized, prohibited capabilities are omitted, structured output uses the existing plan schema, and trusted request bindings cannot be changed;
- provider failure selects deterministic fallback;
- model evaluation records configuration, schema validity, reference defects, policy outcome, latency, and token usage;
- Supermemory search uses a fixed server scope, hybrid mode, limit five, bounded normalized output, no write method, and empty-context fallback;
- malicious memory cannot introduce an undeclared capability or change the trusted-input fingerprint;
- every committed scenario is selectable and reproducible through the typed facade;
- browser-session objects do not share mutable results and reset reconstructs deterministic evidence;
- Judge comparison executes two isolated traces, excludes generated identities from semantic diffs, reports modified, added, removed, and unchanged actions, and preserves provider-fallback provenance;
- mocked Gemini and Supermemory influence is visible without changing trusted inputs, declared capability containment, deterministic policy, terminal state, or verification evidence;
- the Streamlit entrypoint starts without secrets, runs a scenario, exposes every evidence view, and resets through native `AppTest` interaction;
- the whole-home projection distinguishes staged, verified, policy-blocked, execution-failed, and prohibited device states from typed evidence;
- the cinematic layer keeps SVG rotation locally anchored and honors reduced-motion preferences; and
- the nominal fixture verifies eight coordinated simulated effects while fire and gas ignition remain outside the capability registry.

These checks prove the committed implementation against synthetic fixtures. They do not prove model quality for an untested model version, physical correctness, independent sensor integrity, or production security.

## Milestone 4 application evidence

Milestone 4 includes Streamlit import/smoke tests, per-session isolation checks, deterministic reset/replay, provider-disabled startup, one-click Judge comparison, semantic proposal-diff tests, mocked live-provider influence, Gemini failure fallback through the UI, fixed Supermemory scope enforcement, no public memory writes, malicious-memory rejection, and visible trace completeness. Live Gemini and Supermemory calls are not part of validation because the repository does not read real credentials.

## Model evaluation

Model evaluation is separate from deterministic correctness. The implemented harness measures schema validity, capability hallucination, invalid parameters, missing preconditions, deterministic-policy outcome, latency, and token use.

Every result must record model identifier, provider, prompt version, schema version, sampling configuration, and timestamp. Measurements apply only to the observed configuration and are not guarantees for future model versions.

## Prototype acceptance criteria

The hackathon application is demonstrated: the deterministic core operates without Gemini or Supermemory, all six approved reference scenarios are reproducible and selectable in Streamlit, actions have explicit acceptance conditions, prohibited and stale-state actions are rejected, adapter acceptance is never reported as physical verification, every scenario produces an inspectable trace, invalid provider output has no side effects, sessions are isolated, reset is deterministic, and no secret or real household data is required.
