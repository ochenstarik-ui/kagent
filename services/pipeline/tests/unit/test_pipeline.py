import pytest
import httpx
from services.pipeline.src.pipeline import PipelineEngine, PipelineStep, PipelinePhase, StepStatus, PipelineResult
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.fixture
def mock_httpx_client():
    with patch('httpx.AsyncClient') as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = client_instance
        
        # Mock responses based on URL and data
        async def mock_post(url, json=None, **kwargs):
            if "8200/v1/decide" in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"request_id": "req-123"}
                return mock_resp
            elif "8200/v1/execute" in url:
                messages = json.get("messages", []) if json else []
                is_planner = any("planner" in m.get("content", "") for m in messages)
                
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                if is_planner:
                    content = '{"phase": "develop", "description": "Write code", "tool": "file_write", "params": {"path": "test.txt"}}'
                    content = "[" + content + "]"
                    mock_resp.json.return_value = {"success": True, "content": content, "model_id": "test-model", "tokens_input": 10, "tokens_output": 20}
                else:
                    content = '{"tool": "shell", "params": {"command": "echo hello"}}'
                    mock_resp.json.return_value = {"success": True, "content": content, "model_id": "test-model", "tokens_input": 5, "tokens_output": 10}
                return mock_resp
            elif "8300/v1/contexts" in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"status": "ok"}
                return mock_resp
            elif "8300/v1/execute" in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"output": "success"}
                return mock_resp
            else:
                mock_resp = MagicMock()
                mock_resp.status_code = 404
                return mock_resp
                
        client_instance.post = mock_post
        yield client_instance

@pytest.mark.asyncio
async def test_pipeline_execute_success(mock_httpx_client):
    engine = PipelineEngine(event_publisher=AsyncMock())
    result = await engine.execute("task-1", "proj-1", "feature", "Test task")
    
    assert result.status == StepStatus.PASSED
    assert len(result.steps) == 1
    
    step = result.steps[0]
    assert step.phase == PipelinePhase.DEVELOP
    assert step.status == StepStatus.PASSED
    assert step.model_id == "test-model"
    assert step.tokens_input > 0
    
    assert result.total_model_calls == 1
    assert result.total_tokens_input > 0

@pytest.mark.asyncio
async def test_pipeline_boundary_violation(mock_httpx_client):
    engine = PipelineEngine(event_publisher=AsyncMock())
    
    # Overwrite the post method to return a violating step for planner
    async def violating_post(url, json=None, **kwargs):
        if "8200/v1/decide" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"request_id": "req-123"}
            return mock_resp
        elif "8200/v1/execute" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            content = '[{"phase": "develop", "tool": "file_write", "params": {"path": "/etc/passwd"}}]'
            mock_resp.json.return_value = {"success": True, "content": content, "model_id": "test-model"}
            return mock_resp
        elif "8300/v1/contexts" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok"}
            return mock_resp
            
    mock_httpx_client.post = violating_post
    
    result = await engine.execute("task-2", "proj-1", "feature", "Hack task")
    assert result.status == StepStatus.FAILED
    assert result.steps[0].status == StepStatus.FAILED
    assert "violates allowed_paths" in str(result.steps[0].error)

@pytest.mark.asyncio
async def test_pipeline_max_repair_cycles(mock_httpx_client):
    engine = PipelineEngine(event_publisher=AsyncMock())
    
    # Force review to fail repeatedly
    engine.reviewer.review = lambda step: (False, ["Always fails"])
    
    result = await engine.execute("task-3", "proj-1", "feature", "Test repair")
    assert result.status == StepStatus.HUMAN_REQUIRED
    assert result.repair_cycles == result.max_repair_cycles
