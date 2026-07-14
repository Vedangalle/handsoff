# Verification Plan

## Evidence standard

Verification distinguishes requirements, implemented checks, observed results, and future acceptance criteria. Passing Milestone 1 validates contracts, fixtures, and repository foundations only; it is not evidence that runtime safety or product behavior exists.

## Milestone 1 gates

| Gate | Command | Evidence |
|---|---|---|
| Locked installation | `uv sync --frozen --all-extras` | Environment resolves exactly from `uv.lock` without modifying it |
| Formatting | `uv run --frozen ruff format --check .` | All supported source files match the configured formatter |
| Linting | `uv run --frozen ruff check .` | Configured Ruff rules report no defects |
| Static typing | `uv run --frozen mypy src scripts tests` | Strict Python 3.12 type analysis passes |
| Tests | `uv run --frozen coverage run -m pytest` | Unit, property, and contract tests pass with strict pytest configuration |
| Branch coverage | `uv run --frozen coverage report` | Package line and branch coverage meet the configured 100% threshold |
| Lock consistency | `uv lock --check` | Declarations and lockfile agree |
| Dependency audit | `uv run --frozen --all-extras pip-audit --local --cache-dir .cache/pip-audit` | Installed core, development, and optional Gemini dependencies have no reported known vulnerabilities |
| Secret scan | `uv run --frozen python scripts/check_secrets.py` | Git-visible files have no detected candidates; candidate values are never printed |
| Documentation | `uv run --frozen python scripts/check_docs.py` | Required files, local links, and Mermaid fence structure pass |
| Repository boundary | `uv run --frozen python scripts/check_repository.py` | Branch, Python baseline, ignored paths, placeholders, required files, license state, and deferred runtime paths pass |
| Whitespace | `git diff --check` | No whitespace errors are present |

The aggregate command is:

```bash
uv run --frozen --all-extras python scripts/validate.py
```

Before handoff, inspect `git diff --stat`, `git diff --check`, all untracked files, the current branch, and `git status --short --branch`. No files are staged by default.

## Documentation validation limitation

The documentation script verifies relative targets and Mermaid fence structure. Mermaid diagrams must also be visually rendered and reviewed when a renderer becomes part of the documented toolchain. Structural validation is not a full Mermaid parser.

## Milestone 1 contract evidence

The Milestone 1 suite verifies:

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
- all six YAML fixtures validate, round-trip deterministically, and grant no live or R3 authority; and
- scenario expectations cannot contradict or reference undeclared capabilities or conditions.

These checks prove contract behavior. They do not prove that the future policy kernel chooses the correct result or that the future executor follows the transition contracts.

## Future test hierarchy

### Unit tests

Schema rejection, observation freshness and units, policy decisions, risk classification, state transitions, acceptance conditions, idempotency, duplicate suppression, and planner-input minimization.

### Property-based tests

- No invalid transition becomes executable.
- A denied action is never dispatched.
- Expired approval never authorizes execution.
- Duplicate command identifiers produce at most one simulated effect.
- Stale required observations never yield an allowed decision.
- R3 capabilities never execute in a prototype mode.
- Every terminal plan state has a complete ledger trace.

### Contract tests

Capability semantics across adapters, distinct acceptance and verification, shared planner and policy schema, persistence ordering and identity, and rejection of undeclared API fields.

### Integration tests

End-to-end deterministic flow, restart recovery, transaction rollback, planner timeout and invalid output, adapter timeout and contradictory telemetry, duplicate results, and provider-disabled operation.

### Scenario tests

Nominal arrival, false proximity, garage obstruction, demand response, stale telemetry, partial failure, and malicious external text that attempts to create an undeclared capability.

## Future model evaluation

Model evaluation is separate from deterministic correctness. It will measure schema-validity rate, capability-hallucination rate, invalid-parameter rate, missing-precondition rate, deterministic-policy rejection rate, latency, token use, and agreement with hand-authored reference plans.

Every result must record model identifier, provider, prompt version, schema version, sampling configuration, and timestamp. Measurements apply only to the observed configuration and are not guarantees for future model versions.

## Prototype acceptance criteria

The architecture is demonstrated only when the deterministic core operates without Gemini or Supermemory, all six approved reference scenarios are reproducible, actions have explicit preconditions and acceptance conditions, prohibited and stale-state actions are rejected, API acceptance is never reported as physical verification, every scenario produces an inspectable trace, invalid model plans have no side effects, and no secret or real household data is required.

These runtime acceptance criteria are deferred beyond Milestone 1.
