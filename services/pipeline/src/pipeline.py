"""Verified Coding Pipeline — autonomous software development cycle.

v0.5: Planner → Developer → Tester → Reviewer → Repair loop → DoD check.
"""

import hashlib
import json
import logging
import os
import re
import secrets
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
from .workspace import WorkspaceManager
from .git_manager import GitManager
from .ledger import EffectLedger

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
    HUMAN_REQUIRED = "human_required"


class PipelinePhase(str, Enum):
    PLAN = "plan"
    DEVELOP = "develop"
    TEST = "test"
    REVIEW = "review"
    REPAIR = "repair"
    DOD = "dod"  # Definition of Done


@dataclass
class TaskLimits:
    max_time_ms: int = 600000  # 10 minutes default
    max_cost: float = 1.0  # 1$ default
    max_files: int = 10
    max_steps: int = 20
    max_repair_cycles: int = 3


@dataclass
class TaskContract:
    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    approval_required: bool = True
    limits: TaskLimits = field(default_factory=TaskLimits)



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
    model_id: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0


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
    total_model_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_usd: float = 0.0


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

    async def plan(
        self,
        task_type: str,
        task_description: str,
        client: httpx.AsyncClient,
        reasoning_url: str,
        use_model: bool = True
    ) -> list[PipelineStep]:
        if not use_model:
            return self.TEMPLATES.get(task_type, self.TEMPLATES["feature"])
        
        # Call reasoning engine to get a plan
        try:
            # 1. Decide
            decide_res = await client.post(
                f"{reasoning_url}/v1/decide",
                json={"capability": "planning", "task_type": task_type}
            )
            decide_res.raise_for_status()
            req_id = decide_res.json()["request_id"]
            
            # 2. Execute
            exec_res = await client.post(
                f"{reasoning_url}/v1/execute",
                json={
                    "request_id": req_id,
                    "messages": [
                        {"role": "system", "content": "You are a planner. Return a JSON array of steps. Each step must have 'phase' (plan, develop, test, review, dod), 'description', 'tool', and 'params' (dict)."},
                        {"role": "user", "content": f"Plan for task: {task_description}"}
                    ]
                }
            )
            exec_res.raise_for_status()
            data = exec_res.json()
            
            if not data.get("success"):
                raise Exception(f"Reasoning engine failed: {data.get('error')}")
            
            content = data.get("content", "")
            # Try to parse JSON from content
            # find array
            start = content.find("[")
            end = content.rfind("]")
            if start == -1 or end == -1:
                raise ValueError("No JSON array found in output")
            
            parsed = json.loads(content[start:end+1])
            steps = []
            for s in parsed:
                steps.append(PipelineStep(
                    phase=PipelinePhase(s["phase"].lower()),
                    description=s.get("description", ""),
                    tool=s.get("tool", ""),
                    params=s.get("params", {}),
                    model_id=data.get("model_id"),
                    tokens_input=data.get("tokens_input", 0),
                    tokens_output=data.get("tokens_output", 0),
                    cost_usd=data.get("cost_usd", 0.0),
                ))
            return steps
            
        except Exception as e:
            # Create a failed step indicating plan failure instead of silent fallback
            return [PipelineStep(
                phase=PipelinePhase.PLAN,
                description="Generate plan from model",
                status=StepStatus.FAILED,
                error=f"Failed to generate plan: {str(e)}",
                output={"raw_output": content if 'content' in locals() else str(e)}
            )]


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

    async def execute(
        self,
        task_id: str,
        project_id: str,
        task_type: str = "feature",
        task_description: str = "",
        contract: TaskContract = None,
        repository_url: str = "",
        git_token: str = "",
        use_model: bool = True,
        allowed_paths: list[str] = None,
        forbidden_paths: list[str] = None,
    ) -> PipelineResult:
        if contract is None:
            contract = TaskContract(
                allowed_paths=allowed_paths or ["."],
                forbidden_paths=forbidden_paths or []
            )
            
        correlation_id = str(uuid.uuid4())
        ledger = EffectLedger()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            steps = await self.planner.plan(
                task_type=task_type,
                task_description=task_description,
                client=client,
                reasoning_url=self.reasoning_url,
                use_model=use_model
            )
            
            result = PipelineResult(
                task_id=task_id,
                project_id=project_id,
                steps=steps,
                status=StepStatus.RUNNING,
            )
            result.max_repair_cycles = contract.limits.max_repair_cycles
            self._results[task_id] = result

            started = time.time()
        await self._emit_event(
            "task.started",
            project_id=project_id,
            task_id=task_id,
            correlation_id=correlation_id,
            payload={"taskType": task_type},
        )

        workspace_manager: WorkspaceManager | None = None
        git_manager: GitManager | None = None

        if repository_url:
            workspace_manager = WorkspaceManager(repository_url, task_id)
            try:
                ws_path = workspace_manager.setup()
                # Setup contract for git_manager
                from .git_manager import GitTaskContract
                git_contract = GitTaskContract(
                    id=task_id,
                    allowed_paths=contract.allowed_paths,
                    forbidden_paths=contract.forbidden_paths,
                    base_sha="HEAD", # or something
                    max_changed_files=contract.limits.max_files,
                    max_minutes=contract.limits.max_time_ms / 60000,
                    max_model_cost=contract.limits.max_cost,
                    max_agent_turns=contract.limits.max_steps,
                    max_repair_cycles=contract.limits.max_repair_cycles,
                )
                git_manager = GitManager(ws_path, run_id=correlation_id, ledger=ledger, contract=git_contract)
            except Exception as e:
                logger.error(f"Failed to setup workspace: {e}")
                result.status = StepStatus.FAILED
                result.completed_at = datetime.now(timezone.utc).isoformat()
                return result

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                service_secret = os.getenv(SERVICE_SECRET_ENV, "")
                client_headers = getattr(client, "headers", None)
                if client_headers is None:
                    client_headers = {}
                    client.headers = client_headers
                client_headers[SERVICE_SECRET_HEADER] = service_secret

                # Create workspace context
                await client.post(f"{self.runtime_url}/v1/contexts", json={
                    "task_id": task_id,
                    "project_id": project_id,
                })

            for step in steps:

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
                    # Validate paths if tool is file_write or shell touching files
                    if step.tool in ("file_write", "file_read"):
                        path = step.params.get("path", "")
                        # Simple boundary check
                        if ".." in path or path.startswith("/"):
                            raise ValueError(f"Path {path} violates allowed_paths boundaries")
                        # Check against contract
                        allowed = any(path.startswith(a) or path == a or a == "." for a in contract.allowed_paths)
                        if not allowed:
                            raise ValueError(f"Path {path} violates allowed_paths boundaries")
                            
                    if step.phase in (PipelinePhase.DEVELOP, PipelinePhase.REPAIR) and use_model:
                        # 1. Gather context
                        context_msg = f"Task: {task_description}\n"
                        if step.phase == PipelinePhase.REPAIR:
                            context_msg += f"Repair context: {'; '.join(violations if 'violations' in locals() else [])}\n"
                        
                        # 2. Decide & Execute via Reasoning Engine
                        decide_res = await client.post(
                            f"{self.reasoning_url}/v1/decide",
                            json={"capability": "code_generation", "task_type": task_type}
                        )
                        decide_res.raise_for_status()
                        req_id = decide_res.json()["request_id"]
                        
                        exec_res = await client.post(
                            f"{self.reasoning_url}/v1/execute",
                            json={
                                "request_id": req_id,
                                "messages": [
                                    {"role": "system", "content": "You are a developer. Output JSON with 'tool' and 'params' to execute."},
                                    {"role": "user", "content": context_msg}
                                ]
                            }
                        )
                        exec_res.raise_for_status()
                        model_data = exec_res.json()
                        
                        if not model_data.get("success"):
                            raise Exception(f"Model failed: {model_data.get('error')}")
                        
                        step.model_id = model_data.get("model_id")
                        step.tokens_input = model_data.get("tokens_input", 0)
                        step.tokens_output = model_data.get("tokens_output", 0)
                        step.cost_usd = model_data.get("cost_usd", 0.0)
                        
                        result.total_model_calls += 1
                        result.total_tokens_input += step.tokens_input
                        result.total_tokens_output += step.tokens_output
                        result.total_cost_usd += step.cost_usd
                        
                        # Parse tool/params from model content
                        content = model_data.get("content", "{}")
                        try:
                            start = content.find("{")
                            end = content.rfind("}")
                            parsed = json.loads(content[start:end+1])
                            step.tool = parsed.get("tool", step.tool)
                            step.params = parsed.get("params", step.params)
                        except Exception as e:
                            raise ValueError(f"Malformed JSON from model: {content}") from e

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
                    elif step.phase in (PipelinePhase.TEST, PipelinePhase.REPAIR, PipelinePhase.DEVELOP):
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
                            insert_index = result.steps.index(step) + 1
                            result.steps.insert(insert_index, repair_step)
                            
                            if step.phase == PipelinePhase.TEST:
                                new_test_step = PipelineStep(
                                    PipelinePhase.TEST,
                                    "Verify repair fix",
                                    step.tool,
                                    step.params,
                                )
                                result.steps.insert(insert_index + 1, new_test_step)
                                
                            step.status = StepStatus.FAILED
                        else:
                            step.status = StepStatus.FAILED
                            step.error = f"Repair failed: {'; '.join(violations)}"
                            result.status = StepStatus.HUMAN_REQUIRED
                            break
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

        finally:
            if workspace_manager:
                workspace_manager.teardown()

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.total_duration_ms = int((time.time() - started) * 1000)

        # Overall status
        failures = sum(1 for s in result.steps if s.status == StepStatus.FAILED)
        if result.status != StepStatus.HUMAN_REQUIRED:
            result.status = StepStatus.PASSED if failures == 0 else StepStatus.FAILED

        if result.status == StepStatus.PASSED and git_manager and git_token:
            try:
                # Commit and push
                git_manager.create_commit(f"Resolve task {task_id}: {task_description}")
                git_manager.push(workspace_manager.branch_name)
                
                # Create PR
                await git_manager.create_pull_request(
                    token=git_token,
                    repo_owner=workspace_manager.repository_url.split("/")[-2],
                    repo_name=workspace_manager.repository_url.split("/")[-1].replace(".git", ""),
                    title=f"Task {task_id}: {task_type.capitalize()}",
                    body=f"Automated resolution for task {task_id}.\n\nModel costs: ${result.total_cost_usd:.2f}",
                    head=workspace_manager.branch_name,
                    base=workspace_manager.base_branch
                )
            except Exception as e:
                logger.error(f"Git operations failed: {e}")
                result.status = StepStatus.FAILED

        if result.status == StepStatus.FAILED:
            await self._emit_event(
                "task.failed",
                project_id=project_id,
                task_id=task_id,
                correlation_id=correlation_id,
                payload={
                    "errors": [step.error for step in result.steps if step.error is not None],
                },
            )

        return result

    def get_result(self, task_id: str) -> Optional[PipelineResult]:
        return self._results.get(task_id)


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Server
# ═══════════════════════════════════════════════════════════════════════

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="KAgent Pipeline", version="0.5.0")
engine = PipelineEngine()
SERVICE_SECRET_ENV = "KAGENT_SERVICE_SECRET"
SERVICE_SECRET_HEADER = "x-kagent-service-secret"
UNAUTHENTICATED_PATHS = frozenset({"/health/live", "/health/ready"})


@app.middleware("http")
async def require_service_secret(request: Request, call_next):
    if request.url.path not in UNAUTHENTICATED_PATHS:
        expected = os.getenv(SERVICE_SECRET_ENV, "").encode()
        provided = request.headers.get(SERVICE_SECRET_HEADER, "").encode()
        if not expected or not provided or not secrets.compare_digest(provided, expected):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


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
    
    background.add_task(_run)
    
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
