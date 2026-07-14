"""Provider evaluation separate from deterministic runtime correctness."""

from __future__ import annotations

from typing import TYPE_CHECKING

from handsoff.application.capability_registry import CapabilityRegistry
from handsoff.domain.planning import PlannerEvaluationRecord

if TYPE_CHECKING:
    from datetime import datetime

    from handsoff.domain.policies import PolicyEvaluation
    from handsoff.ports.planner import PlannerRequest, PlannerResult


class PlannerEvaluator:
    """Measure declared-reference and contract quality for one planner result."""

    prompt_version = "1.0.0"
    schema_version = "1.0.0"

    def evaluate(  # noqa: PLR0913 - evaluation provenance remains explicit
        self,
        scenario_id: str,
        request: PlannerRequest,
        result: PlannerResult,
        policy: PolicyEvaluation,
        evaluated_at: datetime,
        temperature: float,
    ) -> PlannerEvaluationRecord:
        """Compute observed metrics without treating them as future guarantees."""
        registry = CapabilityRegistry(request.capabilities)
        hallucinations = 0
        invalid_parameters = 0
        missing_preconditions = 0
        for action in result.plan.actions:
            capability = registry.resolve(action.capability_id, action.capability_version)
            if capability is None:
                hallucinations += 1
                continue
            if registry.validate_action(action, result.plan.mode):
                invalid_parameters += 1
            required = {condition.condition_id for condition in capability.preconditions}
            proposed = {condition.condition_id for condition in action.preconditions}
            if not required <= proposed:
                missing_preconditions += 1
        suffix = scenario_id.replace("scenario.", "", 1)
        return PlannerEvaluationRecord(
            evaluation_id=f"evaluation.{suffix}",
            scenario_id=scenario_id,
            provider=result.provider,
            model=result.model,
            prompt_version=self.prompt_version,
            schema_version=self.schema_version,
            temperature=temperature,
            evaluated_at=evaluated_at,
            schema_valid=True,
            capability_hallucination_count=hallucinations,
            invalid_parameter_action_count=invalid_parameters,
            missing_precondition_action_count=missing_preconditions,
            policy_decision=policy.decision,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    def invalid_result(  # noqa: PLR0913 - failure provenance remains explicit
        self,
        scenario_id: str,
        provider: str,
        model: str,
        evaluated_at: datetime,
        temperature: float,
        latency_ms: float,
        failure_reason: str,
    ) -> PlannerEvaluationRecord:
        """Record a schema-invalid or unavailable provider attempt."""
        suffix = scenario_id.replace("scenario.", "", 1)
        return PlannerEvaluationRecord(
            evaluation_id=f"evaluation.{suffix}",
            scenario_id=scenario_id,
            provider=provider,
            model=model,
            prompt_version=self.prompt_version,
            schema_version=self.schema_version,
            temperature=temperature,
            evaluated_at=evaluated_at,
            schema_valid=False,
            capability_hallucination_count=0,
            invalid_parameter_action_count=0,
            missing_precondition_action_count=0,
            policy_decision=None,
            latency_ms=latency_ms,
            failure_reason=failure_reason,
        )


__all__ = ["PlannerEvaluator"]
