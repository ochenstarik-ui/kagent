"""Minimal unit tests for agent runtime module."""

import asyncio
from pathlib import Path

import pytest

from services.agent_runtime.src.runtime import AgentRuntime, FileReadTool, FileWriteTool


def test_file_read_tool():
    tool = FileReadTool()
    assert tool.name == "file_read"


def test_file_write_tool():
    tool = FileWriteTool()
    assert tool.name == "file_write"


@pytest.mark.asyncio
async def test_runtime_create_context():
    runtime = AgentRuntime(Path("/tmp/kagent-test-runtime"))
    ctx = await runtime.create_context("task-1", "project-1")
    assert ctx.task_id == "task-1"
    assert ctx.project_id == "project-1"


@pytest.mark.asyncio
async def test_runtime_execute_unknown_tool():
    runtime = AgentRuntime(Path("/tmp/kagent-test-runtime"))
    await runtime.create_context("task-2", "project-2")
    result = await runtime.execute_tool("task-2", "unknown", {})
    assert "error" in result
