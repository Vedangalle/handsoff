"""Run all committed scenarios through the deterministic runtime."""

from __future__ import annotations

from pathlib import Path

from handsoff.application.run_scenario import ScenarioRunner, load_scenario

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Print concise measured scenario outcomes and fail on any mismatch."""
    assessments = [
        ScenarioRunner().run(load_scenario(path))
        for path in sorted((ROOT / "scenarios").glob("*.yaml"))
    ]
    for assessment in assessments:
        runtime = assessment.runtime
        status = "PASS" if assessment.matched else "FAIL"
        print(
            f"{status} {assessment.scenario_id}: "
            f"policy={runtime.policy.decision.value} "
            f"terminal={runtime.terminal_plan_state.value} "
            f"events={len(runtime.events)}"
        )
        for mismatch in assessment.mismatches:
            print(f"  - {mismatch}")
    return 0 if all(assessment.matched for assessment in assessments) else 1


if __name__ == "__main__":
    raise SystemExit(main())
