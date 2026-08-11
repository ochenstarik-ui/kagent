"""Minimal unit tests for verified coding pipeline."""

import pytest

from services.pipeline.src.pipeline import (
    PipelineEngine,
    PipelinePhase,
    Planner,
    Reviewer,
)


class _NoNetworkClient:
    async def post(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("template planning must not make an HTTP request")


@pytest.mark.asyncio
async def test_planner_returns_steps():
    planner = Planner()
    steps = await planner.plan(
        task_type="feature",
        task_description="Implement a feature",
        client=_NoNetworkClient(),
        reasoning_url="http://reasoning.invalid",
        use_model=False,
    )

    assert steps
    assert steps[0].phase == PipelinePhase.PLAN
    assert {step.phase for step in steps} >= {
        PipelinePhase.DEVELOP,
        PipelinePhase.TEST,
        PipelinePhase.DOD,
    }
    assert all(step.description for step in steps)


def test_reviewer_detects_test_failure():
    reviewer = Reviewer()
    from services.pipeline.src.pipeline import PipelineStep, PipelinePhase, StepStatus

    step = PipelineStep(
        phase=PipelinePhase.TEST,
        description="run tests",
        output={"error": "failed"},
    )
    passed, violations = reviewer.review(step)
    assert passed is False
    assert violations


def test_pipeline_engine_initializes():
    engine = PipelineEngine()
    assert engine.planner is not None
    assert engine.reviewer is not None
