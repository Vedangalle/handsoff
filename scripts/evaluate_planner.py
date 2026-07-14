"""Emit offline planner-evaluation records for committed scenarios."""

from __future__ import annotations

from pathlib import Path

from handsoff.adapters.planner import DeterministicPlanner
from handsoff.application.planner_evaluation import PlannerEvaluator
from handsoff.application.run_scenario import ScenarioRunner, load_scenario
from handsoff.domain.capabilities import AutonomyMode
from handsoff.ports.planner import PlannerRequest

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Evaluate the provider-independent baseline as JSON Lines."""
    planner = DeterministicPlanner()
    evaluator = PlannerEvaluator()
    for path in sorted((ROOT / "scenarios").glob("*.yaml")):
        scenario = load_scenario(path)
        request = PlannerRequest(
            goal=scenario.goal,
            observations=scenario.initial_observations,
            capabilities=scenario.capabilities,
            mode=AutonomyMode.SIMULATION,
            now=scenario.clock_start_at,
        )
        result = planner.propose(request)
        runtime = ScenarioRunner(planner=planner).run(scenario).runtime
        record = evaluator.evaluate(
            scenario_id=scenario.scenario_id,
            request=request,
            result=result,
            policy=runtime.policy,
            evaluated_at=scenario.clock_start_at,
            temperature=0.0,
        )
        print(record.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
