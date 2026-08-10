"""Agent Runtime — isolated worker for single-agent execution.

v0.4: Tool contracts, streaming events, sandbox execution, artifact upload.
"""

import asyncio
import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


# ═══════════════════════════════════════════════════════════════════════
# Tool Contracts
# ═══════════════════════════════════════════════════════════════════════

class ToolPermission(str, Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_SHELL = "execute_shell"
    NETWORK = "network"
    GIT = "git"


@dataclass
class ToolContract:
    """Standardized tool interface for agent capabilities."""
    name: str
    description: str
    permissions: list[ToolPermission]
    parameters: dict[str, Any] = field(default_factory=dict)

    async def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        """Override in subclasses."""
        raise NotImplementedError


class FileReadTool(ToolContract):
    def __init__(self):
        super().__init__(
            name="file_read",
            description="Read contents of a file",
            permissions=[ToolPermission.READ_FILES],
            parameters={
                "path": {"type": "string", "description": "Relative path within workspace"},
            },
        )
    
    async def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        path = workspace / params["path"]
        if not path.resolve().is_relative_to(workspace.resolve()):
            return {"error": "Path escapes workspace"}
        try:
            content = path.read_text(encoding="utf-8")
            return {"content": content, "size": len(content)}
        except Exception as e:
            return {"error": str(e)}


class FileWriteTool(ToolContract):
    def __init__(self):
        super().__init__(
            name="file_write",
            description="Write contents to a file",
            permissions=[ToolPermission.WRITE_FILES],
            parameters={
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
        )
    
    async def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        path = workspace / params["path"]
        if not path.resolve().is_relative_to(workspace.resolve()):
            return {"error": "Path escapes workspace"}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params["content"], encoding="utf-8")
            return {"written": len(params["content"]), "path": str(path.relative_to(workspace))}
        except Exception as e:
            return {"error": str(e)}


class ShellTool(ToolContract):
    def __init__(self):
        super().__init__(
            name="shell",
            description="Execute a shell command (timeout 60s, no network by default)",
            permissions=[ToolPermission.EXECUTE_SHELL],
            parameters={
                "command": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
            },
        )
    
    async def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        cwd = workspace / params.get("cwd", ".")
        try:
            proc = await asyncio.create_subprocess_shell(
                params["command"],
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:10000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5000],
            }
        except asyncio.TimeoutError:
            return {"error": "Command timed out (60s)", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -1}


# ═══════════════════════════════════════════════════════════════════════
# Agent Runtime
# ═══════════════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionEvent:
    type: str  # "step", "tool_call", "tool_result", "artifact", "error"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    task_id: str
    project_id: str
    workspace: Path
    tools: list[ToolContract]
    status: AgentStatus = AgentStatus.IDLE
    events: list[ExecutionEvent] = field(default_factory=list)
    artifacts: list[Path] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentRuntime:
    """Isolated agent execution environment."""
    
    DEFAULT_TOOLS = [FileReadTool(), FileWriteTool(), ShellTool()]
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path(tempfile.mkdtemp(prefix="kagent-"))
        self._contexts: dict[str, AgentContext] = {}
    
    async def create_context(self, task_id: str, project_id: str, tools: Optional[list[ToolContract]] = None) -> AgentContext:
        workspace = self.workspace_root / project_id / task_id
        workspace.mkdir(parents=True, exist_ok=True)
        
        ctx = AgentContext(
            task_id=task_id,
            project_id=project_id,
            workspace=workspace,
            tools=tools or self.DEFAULT_TOOLS[:],
        )
        self._contexts[task_id] = ctx
        return ctx
    
    async def execute_tool(self, task_id: str, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        ctx = self._contexts.get(task_id)
        if not ctx:
            return {"error": f"Context not found: {task_id}"}
        
        tool = next((t for t in ctx.tools if t.name == tool_name), None)
        if not tool:
            return {"error": f"Tool not found: {tool_name}. Available: {[t.name for t in ctx.tools]}"}
        
        # Record event
        ctx.events.append(ExecutionEvent(
            type="tool_call",
            data={"tool": tool_name, "params": params},
        ))
        
        # Execute
        result = await tool.execute(params, ctx.workspace)
        
        ctx.events.append(ExecutionEvent(
            type="tool_result",
            data={"tool": tool_name, "result": result},
        ))
        
        return result
    
    async def save_artifact(self, task_id: str, name: str, content: str) -> str:
        ctx = self._contexts.get(task_id)
        if not ctx:
            raise ValueError(f"Context not found: {task_id}")
        
        path = ctx.workspace / "artifacts" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(content)
        ctx.artifacts.append(path)
        
        ctx.events.append(ExecutionEvent(
            type="artifact",
            data={"name": name, "path": str(path), "size": len(content)},
        ))
        
        return str(path)
    
    async def run(
        self,
        task_id: str,
        steps: list[dict[str, Any]],  # [{tool, params}, ...]
        on_event: Optional[Callable[[ExecutionEvent], None]] = None,
    ) -> AgentContext:
        ctx = self._contexts.get(task_id)
        if not ctx:
            raise ValueError(f"Context not found: {task_id}")
        
        ctx.status = AgentStatus.RUNNING
        ctx.started_at = datetime.now(timezone.utc).isoformat()
        
        try:
            for step in steps:
                event = ExecutionEvent(type="step", data={"step": step})
                ctx.events.append(event)
                if on_event:
                    on_event(event)
                
                result = await self.execute_tool(task_id, step["tool"], step.get("params", {}))
                
                if "error" in result:
                    ctx.status = AgentStatus.FAILED
                    ctx.completed_at = datetime.now(timezone.utc).isoformat()
                    return ctx
            
            ctx.status = AgentStatus.COMPLETED
        except Exception as e:
            ctx.status = AgentStatus.FAILED
            ctx.events.append(ExecutionEvent(type="error", data={"error": str(e)}))
        finally:
            ctx.completed_at = ctx.completed_at or datetime.now(timezone.utc).isoformat()
        
        return ctx
    
    def get_events(self, task_id: str) -> list[ExecutionEvent]:
        ctx = self._contexts.get(task_id)
        return ctx.events if ctx else []
    
    def get_status(self, task_id: str) -> Optional[AgentStatus]:
        ctx = self._contexts.get(task_id)
        return ctx.status if ctx else None
    
    async def cancel(self, task_id: str):
        ctx = self._contexts.get(task_id)
        if ctx and ctx.status == AgentStatus.RUNNING:
            ctx.status = AgentStatus.CANCELLED
            ctx.completed_at = datetime.now(timezone.utc).isoformat()
    
    async def cleanup(self, task_id: str):
        ctx = self._contexts.pop(task_id, None)
        if ctx:
            import shutil
            shutil.rmtree(ctx.workspace, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Server
# ═══════════════════════════════════════════════════════════════════════

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="KAgent Runtime", version="0.4.0")
runtime = AgentRuntime()
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


class CreateContextRequest(BaseModel):
    task_id: str
    project_id: str
    tools: list[str] = Field(default_factory=list)


class ExecuteToolRequest(BaseModel):
    task_id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class RunPipelineRequest(BaseModel):
    task_id: str
    steps: list[dict[str, Any]]
    stream: bool = False


class ToolInfo(BaseModel):
    name: str
    description: str
    permissions: list[str]
    parameters: dict[str, Any]


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": "agent-runtime", "version": "0.4.0"}


@app.get("/v1/tools", response_model=list[ToolInfo])
async def list_tools():
    return [
        ToolInfo(
            name=t.name,
            description=t.description,
            permissions=[p.value for p in t.permissions],
            parameters=t.parameters,
        )
        for t in runtime.DEFAULT_TOOLS
    ]


@app.post("/v1/contexts")
async def create_context(req: CreateContextRequest):
    ctx = await runtime.create_context(req.task_id, req.project_id)
    return {
        "task_id": ctx.task_id,
        "workspace": str(ctx.workspace),
        "status": ctx.status.value,
    }


@app.post("/v1/execute")
async def execute_tool(req: ExecuteToolRequest):
    result = await runtime.execute_tool(req.task_id, req.tool, req.params)
    return result


@app.post("/v1/run")
async def run_pipeline(req: RunPipelineRequest, background: BackgroundTasks):
    async def _run():
        await runtime.run(req.task_id, req.steps)
    
    background.add_task(_run)
    return {
        "task_id": req.task_id,
        "status": "running",
        "steps": len(req.steps),
    }


@app.get("/v1/contexts/{task_id}/events")
async def get_events(task_id: str):
    events = runtime.get_events(task_id)
    return {
        "task_id": task_id,
        "events": [
            {"type": e.type, "timestamp": e.timestamp, "data": e.data}
            for e in events
        ],
    }


@app.get("/v1/contexts/{task_id}/status")
async def get_status(task_id: str):
    status = runtime.get_status(task_id)
    if status is None:
        raise HTTPException(404, "Context not found")
    return {"task_id": task_id, "status": status.value}


@app.delete("/v1/contexts/{task_id}")
async def cleanup_context(task_id: str):
    await runtime.cancel(task_id)
    await runtime.cleanup(task_id)
    return {"status": "cleaned"}
