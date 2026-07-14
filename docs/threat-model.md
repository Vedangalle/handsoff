# Threat Model

## Scope and status

This threat model covers the approved prototype architecture. Milestone 1 implements schema-level controls and negative contract tests, not runtime security controls. The prototype is not approved for consequential hardware or real actuation.

## Protected assets

- Location, occupancy, routines, preferences, and schedules.
- Device credentials, provider tokens, and upstream authority.
- Capability contracts, policy configuration, and approvals.
- Physical safety, property state, and energy use.
- Action history, model prompts, provider responses, and evidence traces.
- Integrity of adapter manifests, dependencies, runtime binaries, and the ledger.

## Adversaries and failure sources

- External attackers with network access.
- Malicious or compromised devices and integrations.
- Prompt injection in calendar, media, weather, telemetry, or memory content.
- Compromised external models or semantic-memory providers.
- Local users without action authority.
- Operator error and unsafe configuration.
- Stale, spoofed, contradictory, or missing telemetry.
- Software defects, duplicate delivery, retries, timeouts, and partial failure.
- Physical conditions the software cannot observe.

## Trust boundaries and abuse paths

| Boundary | Representative abuse | Required response |
|---|---|---|
| User or external text to planner | Prompt injection proposes undeclared action | Treat output as data; strict schema and capability allowlist |
| Telemetry to policy | Stale or spoofed state authorizes unsafe action | Freshness, confidence, source, and contradiction checks; fail closed |
| Planner to policy | Hallucinated capability or parameter | Reject unknown fields, capabilities, versions, and invalid units |
| Policy to executor | Bypass or replay of authority | Versioned decision, approval binding, expiry, and idempotency |
| Executor to adapter | Duplicate or over-broad actuation | Bounded contract, least authority, timeout, retry limit, and revocation |
| Adapter response to verifier | API success represented as physical success | Require independent post-action observation and acceptance conditions |
| Local core to provider | Disclosure of credentials or household context | Minimize and redact; never send credentials |
| Persistence and evidence | Mutation or loss hides unsafe behavior | Append-only events, immutable identifiers, ordering, and integrity checks |

## Mandatory controls

1. No model-to-actuator path.
2. Allowlisted, typed, versioned capability contracts.
3. Unknown fields rejected at trust boundaries.
4. Risk classification and explicit approval policy.
5. Observation freshness and confidence evaluation.
6. Idempotency keys and duplicate-action prevention.
7. Bounded timeouts and retries without unbounded loops.
8. Fail-closed behavior when policy or verification is unavailable.
9. Credentials supplied only through environment or OS credential interfaces.
10. Data minimization before every external call.
11. Append-only evidence for decisions and state transitions.
12. Emergency-stop and adapter-revocation interfaces designed before live mode.

## Risk classes

| Class | Meaning | Prototype handling |
|---|---|---|
| R0 | Read-only observation | Allowed in simulation and shadow mode |
| R1 | Reversible, low-consequence action | Simulated only |
| R2 | Consequential property, privacy, energy, or access action | Simulated; future supervised approval required |
| R3 | Safety-critical, vehicle-motion, life-support, fire, gas, high-energy, or security-critical action | Prohibited |

## Security verification requirements

Later milestones must test invalid transitions, stale observations, capability hallucination, unknown fields, expired approvals, duplicate commands, timeout behavior, malicious external text, provider unavailability, and false success. Security tests must establish negative properties such as “a denied action is never dispatched,” not only successful examples.

Milestone 1 additionally rejects undeclared fields and references, inconsistent policy results, illegal transitions, R3 authorization, non-simulation reference authority, cyclic plans, and contradictory scenario expectations. Repository gates cover dependency vulnerabilities, Git-visible secret candidates, ignored sensitive paths, lock consistency, and milestone scope. These contract, supply-chain, and hygiene checks do not constitute penetration testing or production security evidence.

## Residual risk

- Plausible sensor errors can defeat checks based on the same failure source.
- Actuation and verification may share common hardware or integration failures.
- Users may misunderstand autonomy limits or approval consequences.
- External providers may retain or process context under their own terms.
- Upstream credentials may have broader authority than the adapter surface.
- Physical systems may lack safe compensation or rollback.
- The prototype has no formal verification, penetration test, hardware-in-the-loop evidence, or long-duration reliability data.
