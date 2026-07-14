# Product Charter

## Mission

Give ordinary people safe, interoperable autonomy across the physical systems they already use.

## Vision

A person should be able to describe a desired real-world outcome without manually programming every device, vendor application, condition, and exception. Handsoff should coordinate compatible systems while preserving user authority, local control, and evidence of what actually happened.

## Initial problem

Consumer automation is fragmented across vendors and usually expressed as device commands or trigger-condition-action routines. These systems generally lack a user-owned layer that represents goals and acceptance conditions, reasons across physical domains, checks uncertainty immediately before action, applies model-independent authorization, handles partial failure explicitly, and verifies the final outcome rather than assuming API success.

## Initial user and prototype wedge

The hackathon user is an individual operating a simulated home, vehicle, energy, weather, and media environment. The prototype is an engineering demonstration, not production-ready consumer autonomy.

The first objective is:

> Prepare my environment for arrival in five minutes.

The deterministic simulator coordinates eight nominal whole-home effects: garage entry, charger readiness, room conditioning, guarded coffee preparation, fan speed, ice production, welcome lighting, and television playback. Destination confidence and energy constraints remain authoritative inputs. The suite also demonstrates false proximity, an obstructed garage, an energy constraint, stale telemetry, and partial execution failure.

The presentation wedge is one interactive ecosystem rather than a device dashboard. A cutaway home lets the operator inspect the driveway, car, garage, kitchen, living room, and utility signals as one coordinated result. Visual motion and activity states are projections of typed runtime evidence; they never create authority or substitute for verification. Fire and gas ignition remain visible only as an `R3 locked` boundary.

## Core promise

Given a goal, timestamped world state, declared capabilities, and explicit constraints, the implemented simulation runtime can:

- produce a schema-valid plan;
- explain the plan before execution;
- reject actions outside declared authority;
- execute permitted simulated actions;
- detect incomplete or contradictory outcomes; and
- produce a reproducible evidence trace.

These behaviors are measured against committed synthetic fixtures. They are not evidence of production safety or real-device operation.

## Product principles

1. **Human authority:** the user owns goals, policy, approvals, credentials, and revocation.
2. **Least authority:** adapters expose only typed, bounded capabilities.
3. **Model containment:** model output is untrusted proposed data.
4. **State awareness:** consequential decisions depend on timestamped observations and confidence.
5. **Closed loop:** command acceptance and outcome verification remain separate.
6. **Fail closed:** ambiguity, stale data, conflicts, and unavailable verification prevent actuation.
7. **Local core:** policy, execution state, and the ledger remain local by default.
8. **Provider replaceability:** models, device systems, and memory are adapters.
9. **Progressive autonomy:** simulation, shadow, supervised, and live-bounded modes are distinct.
10. **Evidence before claims:** demonstrations report measured behavior and known limitations.

## Prototype non-goals

- Unrestricted or safety-critical device control.
- Direct control of vehicles, access systems, heaters, pumps, or other consequential hardware.
- Behavior-learning policies without explicit review.
- A general-purpose voice assistant.
- Replacement of Matter, Home Assistant, device firmware, or vendor APIs.
- A cloud account system, multi-tenant service, or mobile application.
- Claims of worldwide novelty, production security, regulatory compliance, or production safety.
- Dependence on Gemini, Supermemory, or any provider for deterministic execution.

## Current status

Milestone 4 completes the hackathon application: deterministic runtime, six reproducible scenarios, append-only evidence, contained Gemini structured planning, deterministic fallback, model evaluation, an interactive whole-home Streamlit interface, and optional read-only Supermemory context. There are no further committed milestones. The prototype still has no real-device integration or actuation.
