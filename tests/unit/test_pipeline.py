"""Minimal unit tests for verified coding pipeline."""

import pytest

from services.pipeline.src.pipeline import PipelineEngine, Planner, Reviewer


def test_planner_returns_steps():
    planner = Planner()
    steps = planner.plan("feature")
    assert len(steps) > 0


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
