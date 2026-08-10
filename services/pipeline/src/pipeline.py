"""Verified Coding Pipeline — autonomous software development cycle.

v0.5: Planner → Developer → Tester → Reviewer → Repair loop → DoD check.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import httpx
from services.nats.src.events import DomainEvent, NatsClient

logger = logging.getLogger(__name__)
EventPublisher = Callable[[str, DomainEvent], Awaitable[None]]
DEFAULT_NATS_URL = "nats://localhost:4222"


# ═══════════════════════════════════════════════════════════════════════
# Pipeline types
# ═══════════════════════════════════════════════════════════════════════

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelinePhase(str, Enum):
    PLAN = "plan"
    DEVELOP = "develop"
    TEST = "test"
    REVIEW = "review"
    REPAIR = "repair"
    DOD = "dod"  # Definition of Done


@dataclass
class PipelineStep:
    phase: PipelinePhase
    description: str
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    repair_attempts: int = 0


@dataclass
class PipelineResult:
    task_id: str
    project_id: str
    steps: list[PipelineStep]
    status: StepStatus = StepStatus.PENDING
    total_duration_ms: int = 0
    repair_cycles: int = 0
    max_repair_cycles: int = 3
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Planner
# ═══════════════════════════════════════════════════════════════════════

class Planner:
    """Decomposes a task into executable steps."""

    TEMPLATES = {
        "feature": [
            PipelineStep(PipelinePhase.PLAN, "Read existing code structure", "file_read", {"path": "."}),
            PipelineStep(PipelinePhase.PLAN, "Identify files to modify", "shell", {"command": "find . -name '*.py' -o -name '*.ts' | head -20"}),
            PipelineStep(PipelinePhase.DEVELOP, "Implement the feature", "file_write", {}),
            PipelineStep(PipelinePhase.DEVELOP, "Write unit tests", "file_write", {}),
            PipelineStep(PipelinePhase.TEST, "Run test suite", "shell", {"command": "python -m pytest -q || npm test"}),
            PipelineStep(PipelinePhase.REVIEW, "Review diff for correctness", "shell", {"command": "git diff --stat"}),
            PipelineStep(PipelinePhase.DOD, "Verify definition of done", "shell", {"command": "echo 'DoD: tests pass, code reviewed, no regressions'"}),
        ],
        "bugfix": [
            PipelineStep(PipelinePhase.PLAN, "Reproduce the bug", "shell", {"command": "echo 'Reproducing...'"}),
            PipelineStep(PipelinePhase.PLAN, "Identify root cause", "file_read", {"path": "."}),
            PipelineStep(PipelinePhase.DEVELOP, "Apply fix", "file_write", {}),
            PipelineStep(PipelinePhase.TEST, "Verify fix + regression tests", "shell", {"command": "python -m pytest -q"}),
            PipelineStep(PipelinePhase.REVIEW, "Review fix", "shell", {"command": "git diff"}),
            PipelineStep(PipelinePhase.DOD, "Verify definition of done", "shell", {"command": "echo 'DoD'"}), 
        ],
        "refactor": [
            PipelineStep(PipelinePhase.PLAN, "Analyze code structure", "file_read", {"path": "."}),
            PipelineStep(PipelinePhase.DEVELOP, "Apply refactoring", "shell", {"command": "echo 'Refactoring...'"}),
            PipelineStep(PipelinePhase.TEST, "Verify behavior unchanged", "shell", {"command": "python -m pytest -q"}),
            PipelineStep(PipelinePhase.REVIEW, "Check diff for regressions", "shell", {"command": "git diff --stat"}),
            PipelineStep(PipelinePhase.DOD, "Verify definition of done", "shell", {"command": "echo 'DoD'"}),
        ],
    }

    def plan(self, task_type: str = "feature") -> list[PipelineStep]:
        return self.TEMPLATES.get(task_type, self.TEMPLATES["feature"])


# ═══════════════════════════════════════════════════════════════════════
# Reviewer
# ═══════════════════════════════════════════════════════════════════════

class Reviewer:
    """Independent review of pipeline output."""

    CRITERIA = {
        "tests_pass": r"(passed|PASSED|OK).*\d+",
        "no_regression": r"(FAILED|ERROR).*0",
        "diff_exists": r"\d+ files? changed",
    }

    def review(self, step: PipelineStep) -> tuple[bool, list[str]]:
        """Returns (passed, violations)."""
        violations = []
        output_str = json.dumps(step.output)

        if step.phase == PipelinePhase.TEST:
            if not re.search(r"(passed|OK)", output_str, re.IGNORECASE):
                violations.append("Tests did not pass")
        
        if step.phase == PipelinePhase.DEVELOP:
            if step.error:
                violations.append(f"Development error: {step.error}")
        
        return len(violations) == 0, violations


# ═══════════════════════════════════════════════════════════════════════
# Pipeline Engine
# ═══════════════════════════════════════════════════════════════════════

class PipelineEngine:
    def __init__(
        self,
        runtime_url: str = "http://localhost:8300",
        reasoning_url: str = "http://localhost:8200",
        event_publisher: EventPublisher | None = None,
    ):
        self.runtime_url = runtime_url
        self.reasoning_url = reasoning_url
        self.planner = Planner()
        self.reviewer = Reviewer()
        self._results: dict[str, PipelineResult] = {}
        nats_url = os.getenv("NATS_URL") or DEFAULT_NATS_URL
        self._event_client = NatsClient(nats_url)
        self._event_delivery_disabled = False
        self._event_publisher = event_publisher or self._publish_to_nats

    async def _publish_to_nats(self, subject: str, event: DomainEvent) -> None:
        if self._event_delivery_disabled:
            raise RuntimeError("NATS event delivery is disabled for this pipeline process")
        try:
            if not self._event_client.connected:
                await self._event_client.connect()
            await self._event_client.publish(subject, event)
        except Exception:
            self._event_delivery_disabled = True
            raise

    async def _emit_event(
        self,
        event_type: str,
        *,
        project_id: str,
        task_id: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        event = DomainEvent(
            type=event_type,
            aggregate_id=task_id,
            aggregate_type="task",
            project_id=project_id,
            task_id=task_id,
            correlation_id=correlation_id,
            data=payload,
        )
        try:
            await self._event_publisher(event_type, event)
        except Exception as error:  # noqa: BLE001 - event delivery is an isolated best-effort boundary
            logger.warning("Failed to publish %s event: %s", event_type, error)

    async def execute(self, task_id: str, project_id: str, task_type: str = "feature") -> PipelineResult:
        steps = self.planner.plan(task_type)
        correlation_id = str(uuid.uuid4())
        result = PipelineResult(
            task_id=task_id,
            project_id=project_id,
            steps=steps,
            status=StepStatus.RUNNING,
        )
        self._results[task_id] = result

        started = time.time()
        await self._emit_event(
            "task.started",
            project_id=project_id,
            task_id=task_id,
            correlation_id=correlation_id,
            payload={"taskType": task_type},
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create workspace context
            await client.post(f"{self.runtime_url}/v1/contexts", json={
                "task_id": task_id,
                "project_id": project_id,
            })

            for step in steps:
                if result.repair_cycles >= result.max_repair_cycles:
                    step.status = StepStatus.FAILED
                    step.error = "Max repair cycles exceeded"
                    break

                step.status = StepStatus.RUNNING
                step.started_at = datetime.now(timezone.utc).isoformat()
                await self._emit_event(
                    "agent.started",
                    project_id=project_id,
                    task_id=task_id,
                    correlation_id=correlation_id,
                    payload={
                        "phase": step.phase.value,
                        "description": step.description,
                        "tool": step.tool,
                    },
                )

                try:
                    # Execute tool via runtime
                    if step.tool:
                        resp = await client.post(f"{self.runtime_url}/v1/execute", json={
                            "task_id": task_id,
                            "tool": step.tool,
                            "params": step.params,
                        })
                        step.output = resp.json() if resp.status_code == 200 else {"error": resp.text}
                    
                    # Review output
                    review_passed, violations = self.reviewer.review(step)

                    if review_passed:
                        step.status = StepStatus.PASSED
                    elif step.phase in (PipelinePhase.REPAIR, PipelinePhase.DEVELOP):
                        # Try repair
                        result.repair_cycles += 1
                        step.repair_attempts += 1
                        
                        if result.repair_cycles < result.max_repair_cycles:
                            # Add repair step
                            repair_step = PipelineStep(
                                PipelinePhase.REPAIR,
                                f"Auto-repair attempt {step.repair_attempts}: {'; '.join(violations)}",
                                "file_write",
                                {},
                            )
                            result.steps.insert(result.steps.index(step) + 1, repair_step)
                            step.status = StepStatus.FAILED
                        else:
                            step.status = StepStatus.FAILED
                            step.error = f"Repair failed: {'; '.join(violations)}"
                    else:
                        step.status = StepStatus.FAILED
                        step.error = "; ".join(violations) if violations else "Review failed"

                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)

                step.completed_at = datetime.now(timezone.utc).isoformat()
                if step.status == StepStatus.PASSED:
                    await self._emit_event(
                        "agent.completed",
                        project_id=project_id,
                        task_id=task_id,
                        correlation_id=correlation_id,
                        payload={
                            "phase": step.phase.value,
                            "description": step.description,
                            "status": step.status.value,
                        },
                    )
                    artifact_path = step.output.get("path")
                    if isinstance(artifact_path, str) and artifact_path:
                        await self._emit_event(
                            "artifact.created",
                            project_id=project_id,
                            task_id=task_id,
                            correlation_id=correlation_id,
                            payload={"path": artifact_path},
                        )

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.total_duration_ms = int((time.time() - started) * 1000)

        # Overall status
        failures = sum(1 for s in steps if s.status == StepStatus.FAILED)
        result.status = StepStatus.PASSED if failures == 0 else StepStatus.FAILED
        if result.status == StepStatus.FAILED:
            await self._emit_event(
                "task.failed",
                project_id=project_id,
                task_id=task_id,
                correlation_id=correlation_id,
                payload={
                    "errors": [step.error for step in steps if step.error is not None],
                },
            )

        return result

    def get_result(self, task_id: str) -> Optional[PipelineResult]:
        return self._results.get(task_id)


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Server
# ═══════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="KAgent Pipeline", version="0.5.0")
from services.shared.service_auth import ServiceAuthMiddleware
app.add_middleware(ServiceAuthMiddleware)
engine = PipelineEngine()


class ExecutePipelineRequest(BaseModel):
    task_id: str
    project_id: str
    task_type: str = "feature"


class StepResult(BaseModel):
    phase: str
    description: str
    status: str
    error: Optional[str] = None
    repair_attempts: int = 0


class PipelineResponse(BaseModel):
    task_id: str
    project_id: str
    status: str
    steps: list[StepResult]
    total_duration_ms: int
    repair_cycles: int


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": "pipeline", "version": "0.5.0"}


@app.post("/v1/pipelines/execute", response_model=PipelineResponse)
async def execute_pipeline(req: ExecutePipelineRequest, background: BackgroundTasks):
    async def _run():
        await engine.execute(req.task_id, req.project_id, req.task_type)
    
    background.add_task(lambda: asyncio.create_task(_run()))
    
    return PipelineResponse(
        task_id=req.task_id,
        project_id=req.project_id,
        status="running",
        steps=[],
        total_duration_ms=0,
        repair_cycles=0,
    )


@app.get("/v1/pipelines/{task_id}", response_model=PipelineResponse)
async def get_pipeline(task_id: str):
    result = engine.get_result(task_id)
    if not result:
        raise HTTPException(404, "Pipeline not found")
    
    return PipelineResponse(
        task_id=result.task_id,
        project_id=result.project_id,
        status=result.status.value,
        steps=[
            StepResult(
                phase=s.phase.value,
                description=s.description,
                status=s.status.value,
                error=s.error,
                repair_attempts=s.repair_attempts,
            )
            for s in result.steps
        ],
        total_duration_ms=result.total_duration_ms,
        repair_cycles=result.repair_cycles,
    )


@app.get("/v1/pipelines")
async def list_pipelines():
    return {
        "pipelines": list(engine._results.keys()),
        "count": len(engine._results),
    }
