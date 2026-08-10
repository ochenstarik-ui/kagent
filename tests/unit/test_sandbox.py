import os
from unittest.mock import patch
import pytest
from pathlib import Path

from services.agent_runtime.src.runtime import AgentRuntime, ShellTool, FileReadTool, FileWriteTool

@pytest.fixture
def mock_bwrap():
    with patch("os.path.exists") as mock_exists:
        # Make os.path.exists return True ONLY for /usr/bin/bwrap, fallback to original for others
        original_exists = os.path.exists
        def side_effect(path):
            if path == "/usr/bin/bwrap":
                return True
            return original_exists(path)
        mock_exists.side_effect = side_effect
        yield mock_exists


@pytest.mark.asyncio
async def test_shell_tool_missing_bwrap():
    # If bwrap is missing, shell tool fails
    tool = ShellTool()
    with patch("os.path.exists", return_value=False):
        result = await tool.execute({"command": "echo 1"}, Path("/tmp/ws"))
    assert "error" in result
    assert "Isolation unavailable" in result["error"]


@pytest.mark.asyncio
async def test_agent_runtime_missing_bwrap():
    # If bwrap is missing, agent runtime fails to execute ANY tool
    runtime = AgentRuntime(Path("/tmp/kagent-test-runtime"))
    ctx = await runtime.create_context("task-x", "project-x")
    
    with patch("os.path.exists", return_value=False):
        result = await runtime.execute_tool("task-x", "shell", {"command": "echo 1"})
    assert "error" in result
    assert "Isolation unavailable" in result["error"]


@pytest.mark.asyncio
async def test_shell_tool_with_bwrap_command_construction(mock_bwrap):
    tool = ShellTool()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = mock_exec.return_value
        mock_proc.communicate.return_value = (b"hello\n", b"")
        mock_proc.returncode = 0
        
        result = await tool.execute({"command": "echo hello"}, Path("/tmp/ws"))
        
        assert result["exit_code"] == 0
        assert result["stdout"] == "hello\n"
        
        # Verify bwrap was called with unshare-all
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "/usr/bin/bwrap"
        assert "--unshare-all" in args
        assert "--tmpfs" in args
        
        # Verify env is empty to avoid leaking secrets
        kwargs = mock_exec.call_args[1]
        assert kwargs.get("env") == {}


@pytest.mark.asyncio
async def test_shell_tool_negative_network_isolation(mock_bwrap):
    # This is a unit test checking that we don't pass --share-net
    tool = ShellTool()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = mock_exec.return_value
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        
        await tool.execute({"command": "curl 1.1.1.1"}, Path("/tmp/ws"))
        args = mock_exec.call_args[0]
        assert "--unshare-all" in args
        assert "--share-net" not in args

@pytest.mark.asyncio
async def test_shell_tool_negative_path_escape(mock_bwrap):
    tool = ShellTool()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = mock_exec.return_value
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        
        # Test shell tool cwd isolation
        workspace = Path("/tmp/ws")
        await tool.execute({"cwd": "../out", "command": "cat /etc/passwd"}, workspace)
        
        args = mock_exec.call_args[0]
        # Bwrap should only bind the workspace, not the parent
        bind_index = args.index("--bind")
        assert args[bind_index + 1] == str(workspace.resolve())
        assert args[bind_index + 2] == str(workspace.resolve())

@pytest.mark.asyncio
async def test_file_read_tool_escape():
    tool = FileReadTool()
    result = await tool.execute({"path": "../../../etc/passwd"}, Path("/tmp/ws"))
    assert "error" in result
    assert "Path escapes workspace" in result["error"]

@pytest.mark.asyncio
async def test_file_write_tool_escape():
    tool = FileWriteTool()
    result = await tool.execute({"path": "../../../etc/passwd", "content": "hack"}, Path("/tmp/ws"))
    assert "error" in result
    assert "Path escapes workspace" in result["error"]
