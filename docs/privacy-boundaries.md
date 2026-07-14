# Privacy Boundaries

## Purpose

Handsoff may eventually process location, occupancy, routines, schedules, device state, media context, energy use, goals, approvals, and action history. These data can reveal sensitive household behavior even when no field is labeled personal information.

Milestone 4 processes only synthetic, simulation-labeled fixtures. The deterministic path contacts no provider. Gemini and read-only Supermemory are explicit optional modes and are never invoked by validation with real credentials. No real household data is accepted.

## Data zones

| Zone | Examples | Default handling |
|---|---|---|
| Local trusted core | Policy, execution state, approvals, operational ledger | Local storage; least-privilege access |
| Local untrusted input | User text, telemetry, adapter manifests, imported context | Validate, normalize, timestamp, and constrain before use |
| Credential interface | Provider tokens and device credentials | Environment or OS credential interface; never persisted in plans, prompts, logs, or source |
| External provider | Gemini and optional semantic memory | Minimized, documented disclosure only after explicit configuration |
| Evidence export | Traces, reports, screenshots | Redact and review before leaving the local boundary |

## Mandatory rules

1. Local-first describes the trusted operational core; it is not a claim that all configured data remains on-device.
2. Every provider call crosses a trust boundary and must identify the provider, purpose, fields sent, retention assumptions, and failure behavior.
3. Credentials must never enter model context, memory content, telemetry, scenarios, logs, screenshots, tests, or version control.
4. Prompts contain only the minimum state required to propose a plan. Stable pseudonymous identifiers are preferred over names or addresses.
5. Optional memory may provide preference context but cannot grant authority, change policy, execute actions, or verify outcomes.
6. The local ledger records sufficient evidence for reproducibility without copying unnecessary provider payloads or household content.
7. Logs and exported traces must be structured for redaction and must not default to raw request or response bodies.
8. Data retention and deletion controls must be defined before any real household or provider data is accepted.

## Credential handling

`.env.example` contains variable names with empty values only. Real values belong in an ignored local environment file or OS credential store. Repository tools must enumerate Git-visible files and must not read ignored environment files during validation.

Future credential interfaces must support revocation, rotation, least privilege, and clear ownership. Home Assistant or vendor credentials may grant broader permissions than an adapter exposes; adapter allowlists do not reduce the upstream credential's actual authority.

## External providers

Gemini may receive a minimized snapshot for typed plan proposal generation. Supermemory, if added, may receive or retrieve long-horizon preference or prior-outcome context. Neither provider belongs in deterministic policy, authority, execution, or verification.

Before the Supermemory adapter or any non-simulated data path is implemented, its documentation must specify:

- exact input and output fields;
- provider account and region assumptions;
- retention and training settings available to the operator;
- timeout, unavailability, and deletion behavior;
- redaction and minimization steps; and
- observable evidence that the deterministic core still functions when disabled.

The Gemini prompt builder excludes adapter IDs, source-adapter IDs, correlation IDs, credentials, prohibited capabilities, and capabilities unavailable in the active mode. Supermemory uses one server-bound demo scope, hybrid read-only search, a five-result maximum, and 500-character normalized items. Optional memory text is labeled as untrusted external context and never enters policy, approval, execution, verification, or authoritative ledger state. See the [Streamlit deployment guide](streamlit-deployment.md).

## Residual privacy risk

Minimized data may still be identifying when combined with timing, location, or routine patterns. Provider policies and retention behavior may change. A local compromise can expose the ledger or credentials. Screenshots and demonstrations can reveal household context. These risks require review before any non-simulated data is introduced.
