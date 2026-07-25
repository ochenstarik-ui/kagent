"""Multi-Agent Orchestration — coordinate multiple agents for complex workflows.

v0.8: Agent pool, task delegation, consensus, handoff protocol.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════════════
# Domain types
# ═══════════════════════════════════════════════════════════════════════

class AgentRole(str, Enum):
    PLANNER = "planner"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    RESEARCHER = "researcher"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentInfo:
    id: str
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    current_task: Optional[str] = None
    completed_tasks: int = 0
    error_count: int = 0


@dataclass
class WorkItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HandoffContext:
    """Context passed between agents during handoff."""
    from_agent: str
    to_agent: str
    task_context: dict[str, Any]
    artifacts: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ═══════════════════════════════════════════════════════════════════════
# Agent Pool
# ═══════════════════════════════════════════════════════════════════════

class AgentPool:
    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._work_queue: list[WorkItem] = []
        self._completed: list[WorkItem] = []
        self._handoff_log: list[HandoffContext] = []

    def register(self, role: AgentRole, capabilities: Optional[list[str]] = None) -> AgentInfo:
        agent = AgentInfo(
            id=f"{role.value}-{str(uuid.uuid4())[:8]}",
            role=role,
            capabilities=capabilities or [],
        )
        self._agents[agent.id] = agent
        return agent

    def get_available(self, role: Optional[AgentRole] = None) -> list[AgentInfo]:
        available = [a for a in self._agents.values() if a.status == AgentStatus.IDLE]
        if role:
            available = [a for a in available if a.role == role]
        return available

    def assign_task(self, agent_id: str, item: WorkItem) -> bool:
        agent = self._agents.get(agent_id)
        if not agent or agent.status != AgentStatus.IDLE:
            return False
        agent.status = AgentStatus.BUSY
        agent.current_task = item.id
        item.assigned_agent = agent_id
        item.status = "assigned"
        return True

    def complete_task(self, agent_id: str, result: dict[str, Any]) -> Optional[WorkItem]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        item = next((w for w in self._work_queue if w.id == agent.current_task), None)
        if item:
            item.status = "completed" if "error" not in result else "failed"
            item.result = result
            self._completed.append(item)
            self._work_queue.remove(item)
        agent.status = AgentStatus.IDLE
        agent.completed_tasks += 1
        agent.current_task = None
        if "error" in result:
            agent.error_count += 1
        return item

    def enqueue(self, item: WorkItem) -> None:
        # Sort by priority
        self._work_queue.append(item)
        self._work_queue.sort(key=lambda w: {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }[w.priority])

    def get_next_task(self) -> Optional[WorkItem]:
        # Return highest priority pending task with no uncompleted dependencies
        for item in self._work_queue:
            if item.status == "pending":
                deps_ready = all(
                    any(c.id == dep and c.status == "completed" for c in self._completed)
                    for dep in item.dependencies
                )
                if deps_ready:
                    return item
        return None

    def handoff(self, from_agent: str, to_agent: str, context: dict, artifacts: Optional[list[str]] = None) -> HandoffContext:
        h = HandoffContext(
            from_agent=from_agent,
            to_agent=to_agent,
            task_context=context,
            artifacts=artifacts or [],
        )
        self._handoff_log.append(h)
        return h

    def get_stats(self) -> dict[str, Any]:
        agents = [
            {
                "id": a.id,
                "role": a.role.value,
                "status": a.status.value,
                "completed": a.completed_tasks,
                "errors": a.error_count,
            }
            for a in self._agents.values()
        ]
        return {
            "agents": agents,
            "queue_depth": len(self._work_queue),
            "completed": len(self._completed),
            "handoffs": len(self._handoff_log),
        }


pool = AgentPool()


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Server
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(title="KAgent Orchestrator", version="0.8.0")


class RegisterAgentRequest(BaseModel):
    role: str
    capabilities: list[str] = []


class CreateWorkItemRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "normal"
    dependencies: list[str] = []


class AssignTaskRequest(BaseModel):
    agent_id: str


class CompleteTaskRequest(BaseModel):
    agent_id: str
    result: dict[str, Any] = {}


class HandoffRequest(BaseModel):
    from_agent: str
    to_agent: str
    context: dict[str, Any]
    artifacts: list[str] = []


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": "orchestrator", "version": "0.8.0"}


@app.post("/v1/agents/register")
async def register_agent(req: RegisterAgentRequest):
    agent = pool.register(AgentRole(req.role), req.capabilities)
    return {"agent_id": agent.id, "role": agent.role.value, "status": agent.status.value}


@app.get("/v1/agents")
async def list_agents():
    return {
        "agents": [
            {"id": a.id, "role": a.role.value, "status": a.status.value, "completed": a.completed_tasks}
            for a in pool._agents.values()
        ]
    }


@app.get("/v1/agents/available")
async def available_agents(role: Optional[str] = None):
    agents = pool.get_available(AgentRole(role) if role else None)
    return {"agents": [{"id": a.id, "role": a.role.value} for a in agents]}


@app.post("/v1/work")
async def create_work(req: CreateWorkItemRequest):
    item = WorkItem(
        title=req.title,
        description=req.description,
        priority=TaskPriority(req.priority),
        dependencies=req.dependencies,
    )
    pool.enqueue(item)
    return {"work_id": item.id, "status": item.status, "priority": item.priority.value}


@app.get("/v1/work")
async def list_work():
    return {
        "queue": [
            {"id": w.id, "title": w.title, "status": w.status, "priority": w.priority.value}
            for w in pool._work_queue
        ],
        "completed": [
            {"id": w.id, "title": w.title, "status": w.status}
            for w in pool._completed[-20:]
        ],
    }


@app.post("/v1/work/assign")
async def assign_work(req: AssignTaskRequest):
    next_task = pool.get_next_task()
    if not next_task:
        raise HTTPException(404, "No pending tasks available")

    ok = pool.assign_task(req.agent_id, next_task)
    if not ok:
        raise HTTPException(409, "Agent not available")

    return {"work_id": next_task.id, "agent_id": req.agent_id, "title": next_task.title}


@app.post("/v1/work/complete")
async def complete_work(req: CompleteTaskRequest):
    item = pool.complete_task(req.agent_id, req.result)
    if not item:
        raise HTTPException(404, "No active task for agent")
    return {"work_id": item.id, "status": item.status, "result": item.result}


@app.post("/v1/handoff")
async def handoff(req: HandoffRequest):
    ctx = pool.handoff(req.from_agent, req.to_agent, req.context, req.artifacts)
    return {
        "handoff_id": ctx.handoff_id,
        "from": ctx.from_agent,
        "to": ctx.to_agent,
    }


@app.get("/v1/stats")
async def stats():
    return pool.get_stats()


# Auto-start: register default agents on startup
@app.on_event("startup")
async def startup():
    pool.register(AgentRole.PLANNER, ["planning", "research"])
    pool.register(AgentRole.DEVELOPER, ["code_generation", "code_review"])
    pool.register(AgentRole.DEVELOPER, ["code_generation"])
    pool.register(AgentRole.REVIEWER, ["code_review", "analysis"])
    pool.register(AgentRole.TESTER, ["testing", "verification"])
    pool.register(AgentRole.RESEARCHER, ["research", "analysis"])
    pool.register(AgentRole.ORCHESTRATOR, ["orchestration"])
