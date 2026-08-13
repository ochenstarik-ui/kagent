import os
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import httpx

from src.server import app, engine, DECISION_CACHE

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown(monkeypatch):
    DECISION_CACHE.clear()
    engine.telemetry.clear()
    
    # Setup mock account for opencode-go and xai so tests don't fail due to empty pool
    engine.registry.set_provider_pool("opencode-go", "http://mock", {"oc-1": "test-key-1"})
    engine.registry.set_provider_pool("xai", "http://mock", {"xai-1": "test-key-2"})
    engine.registry.set_role_pool("default", ["oc-1", "xai-1"])
    
    monkeypatch.setenv("EXECUTION_MODE", "live")
    yield

def test_unknown_request_id():
    response = client.post("/v1/execute", json={"request_id": "missing", "messages": []})
    assert response.status_code == 404

def test_execute_success():
    decide_res = client.post("/v1/decide", json={"capability": "reasoning"})
    assert decide_res.status_code == 200
    req_id = decide_res.json()["request_id"]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "choices": [{"message": {"content": "Success!"}}]
        }
        mock_post.return_value = mock_response
        
        exec_res = client.post("/v1/execute", json={"request_id": req_id, "messages": [{"role": "user", "content": "hello"}]})
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is True
        assert data["tokens_input"] == 100
        assert data["tokens_output"] == 50
        assert data["content"] == "Success!"

def test_fallback_on_error():
    decide_res = client.post("/v1/decide", json={"capability": "reasoning"})
    req_id = decide_res.json()["request_id"]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        def side_effect(*args, **kwargs):
            if mock_post.call_count == 1:
                raise Exception("First model failed")
            
            mock_response = MagicMock()
            mock_response.raise_for_status = lambda: None
            mock_response.json.return_value = {
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                "choices": [{"message": {"content": "Fallback success!"}}]
            }
            return mock_response
            
        mock_post.side_effect = side_effect
        
        exec_res = client.post("/v1/execute", json={"request_id": req_id, "messages": [{"role": "user", "content": "hello"}]})
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is True
        assert data["content"] == "Fallback success!"
        assert mock_post.call_count == 2
        assert len(engine.telemetry) == 2
        assert engine.telemetry[0].success is False

def test_exhaustion_returns_error():
    decide_res = client.post("/v1/decide", json={"capability": "reasoning"})
    req_id = decide_res.json()["request_id"]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("All fail")
        
        exec_res = client.post("/v1/execute", json={"request_id": req_id, "messages": [{"role": "user", "content": "hello"}]})
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is False
        assert "All fail" in data["error"]

def test_timeout():
    decide_res = client.post("/v1/decide", json={"capability": "reasoning"})
    req_id = decide_res.json()["request_id"]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timeout")
        
        exec_res = client.post("/v1/execute", json={"request_id": req_id, "messages": [{"role": "user", "content": "hello"}]})
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is False
        assert "Timeout" in data["error"]

def test_replay_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "replay")
    monkeypatch.chdir(tmp_path)
    
    decide_res = client.post("/v1/decide", json={"capability": "reasoning"})
    req_id = decide_res.json()["request_id"]
    
    with pytest.raises(FileNotFoundError):
        client.post("/v1/execute", json={"request_id": req_id, "messages": []})
    
    cassettes_dir = tmp_path / "cassettes"
    cassettes_dir.mkdir(exist_ok=True)
    import hashlib
    req_hash = hashlib.sha256(json.dumps({"messages": [{"role": "user", "content": "replay"}]}).encode()).hexdigest()[:16]
    c_file = cassettes_dir / f"{req_id}_{req_hash}.json"
    with c_file.open("w", encoding="utf-8") as f:
        json.dump({
            "tokens_input": 5,
            "tokens_output": 5,
            "cost_usd": 0.01,
            "latency_ms": 100,
            "content": "replayed content",
        }, f)
    
    exec_res = client.post("/v1/execute", json={"request_id": req_id, "messages": [{"role": "user", "content": "replay"}]})
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is True
    assert data["content"] == "replayed content"

