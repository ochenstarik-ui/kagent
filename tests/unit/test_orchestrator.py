"""Minimal unit tests for multi-agent orchestrator."""

import pytest

from services.orchestrator.src.orchestrator import AgentPool, AgentRole, WorkItem


def test_register_agent():
    pool = AgentPool()
    agent = pool.register(AgentRole.DEVELOPER, ["python"])
    assert agent.role == AgentRole.DEVELOPER
    assert "python" in agent.capabilities


def test_assign_task():
    pool = AgentPool()
    agent = pool.register(AgentRole.DEVELOPER)
    item = WorkItem(title="test task")
    pool.enqueue(item)
    next_task = pool.get_next_task()
    assert next_task is not None
    assert pool.assign_task(agent.id, next_task)


def test_handoff():
    pool = AgentPool()
    ctx = pool.handoff("agent-1", "agent-2", {"task": "test"})
    assert ctx.from_agent == "agent-1"
    assert ctx.to_agent == "agent-2"
