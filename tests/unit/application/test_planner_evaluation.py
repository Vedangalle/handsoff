"""Planner-evaluation harness tests."""

from __future__ import annotations

from handsoff.application.planner_evaluation import PlannerEvaluator
from handsoff.domain.capabilities import AutonomyMode
from handsoff.ports.planner import PlannerRequest, PlannerResult
from tests.fixtures.contracts import (
    NOW,
    make_action,
    make_capability,
    make_goal,
    make_observation,
    make_plan,
    make_policy_evaluation,
)

EXPECTED_INPUT_TOKENS = 10


def test_planner_evaluator_counts_reference_defects() -> None:
    """Hallucinations, invalid parameters, and missing preconditions are separate metrics."""
    condition = make_goal().acceptance_conditions[0]
    capability = make_capability(preconditions=(condition,))
    known_action = make_action(parameters={"undeclared": 1}, preconditions=())
    unknown_action = make_action(
        action_id="action.unknown",
        capability_id="unknown.prepare",
        idempotency_key="idempotency.unknown",
    )
    plan = make_plan(actions=(known_action, unknown_action))
    request = PlannerRequest(
        goal=make_goal(),
        observations=(make_observation(),),
        capabilities=(capability,),
        mode=AutonomyMode.SIMULATION,
        now=NOW,
    )
    result = PlannerResult(
        plan=plan,
        provider="test",
        model="model",
        used_fallback=False,
        latency_ms=12.0,
        input_tokens=EXPECTED_INPUT_TOKENS,
        output_tokens=5,
    )
    policy = make_policy_evaluation()
    record = PlannerEvaluator().evaluate(
        "scenario.nominal",
        request,
        result,
        policy,
        NOW,
        0.0,
    )
    assert record.capability_hallucination_count == 1
    assert record.invalid_parameter_action_count == 1
    assert record.missing_precondition_action_count == 1
    assert record.input_tokens == EXPECTED_INPUT_TOKENS


def test_planner_evaluator_records_invalid_provider_result() -> None:
    """Schema failure evidence does not invent quality or policy metrics."""
    record = PlannerEvaluator().invalid_result(
        scenario_id="scenario.nominal",
        provider="google",
        model="gemini-test",
        evaluated_at=NOW,
        temperature=0.0,
        latency_ms=5.0,
        failure_reason="structured output failed validation",
    )
    assert not record.schema_valid
    assert record.policy_decision is None
    assert record.failure_reason == "structured output failed validation"


def test_planner_evaluator_accepts_valid_precondition_complete_action() -> None:
    """A clean declared action contributes zero defect counts."""
    condition = make_goal().acceptance_conditions[0]
    capability = make_capability(preconditions=(condition,))
    action = make_action(preconditions=(condition,))
    plan = make_plan(actions=(action,))
    request = PlannerRequest(
        goal=make_goal(),
        observations=(make_observation(),),
        capabilities=(capability,),
        mode=AutonomyMode.SIMULATION,
        now=NOW,
    )
    record = PlannerEvaluator().evaluate(
        "scenario.clean",
        request,
        PlannerResult(
            plan=plan,
            provider="test",
            model="model",
            used_fallback=False,
            latency_ms=0.0,
        ),
        make_policy_evaluation(),
        NOW,
        0.0,
    )
    assert record.invalid_parameter_action_count == 0
    assert record.missing_precondition_action_count == 0
