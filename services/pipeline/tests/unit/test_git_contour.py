import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from services.pipeline.src.git import GitManager
from services.pipeline.src.ledger import EffectLedger
from services.pipeline.src.workspace import WorkspaceManager


@pytest.fixture
def local_repo():
    temp_dir = tempfile.mkdtemp(prefix="kagent_test_repo_")
    repo_dir = Path(temp_dir)
    
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True)
    
    (repo_dir / "README.md").write_text("Hello")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    
    # Create main branch if not default
    subprocess.run(["git", "branch", "-m", "main"], cwd=repo_dir, check=False)
    
    yield repo_dir
    
    # Cleanup
    import shutil
    import stat
    def handle_remove_readonly(func, path, exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(repo_dir, onerror=handle_remove_readonly)


def test_workspace_manager(local_repo):
    wm = WorkspaceManager(repository_url=str(local_repo), task_id="test-1")
    ws_path = wm.setup()
    
    assert ws_path.exists()
    assert (ws_path / "README.md").exists()
    
    # Check branch
    result = subprocess.run(["git", "branch", "--show-current"], cwd=ws_path, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "kagent/task-test-1"
    
    # Artifacts dir exists
    assert wm.artifacts_dir.exists()
    
    # Teardown
    wm.teardown()
    assert not ws_path.exists()
    assert wm.artifacts_dir.exists()


def test_git_manager_paths(local_repo):
    wm = WorkspaceManager(repository_url=str(local_repo), task_id="test-2")
    ws_path = wm.setup()
    ledger = EffectLedger()
    gm = GitManager(ws_path, ledger)
    
    # Modify allowed file
    (ws_path / "allowed.txt").write_text("allowed")
    assert gm.verify_paths(["allowed.txt"]) is True
    
    # Modify forbidden file
    (ws_path / "forbidden.txt").write_text("forbidden")
    assert gm.verify_paths(["allowed.txt"]) is False
    
    wm.teardown()


def test_git_manager_commit(local_repo):
    wm = WorkspaceManager(repository_url=str(local_repo), task_id="test-3")
    ws_path = wm.setup()
    ledger = EffectLedger()
    gm = GitManager(ws_path, ledger)
    
    (ws_path / "new_file.txt").write_text("content")
    gm.commit_changes("task-3", "run-1", "Test message")
    
    result = subprocess.run(["git", "log", "-1"], cwd=ws_path, capture_output=True, text=True, check=True)
    log = result.stdout
    assert "Task-ID: task-3" in log
    assert "Run-ID: run-1" in log
    
    wm.teardown()


@pytest.mark.asyncio
async def test_git_manager_pr_idempotency(local_repo, monkeypatch):
    wm = WorkspaceManager(repository_url=str(local_repo), task_id="test-4")
    ws_path = wm.setup()
    ledger = EffectLedger()
    gm = GitManager(ws_path, ledger)
    
    mock_post = AsyncMock()
    mock_resp = __import__("unittest").mock.MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"html_url": "http://pr"}
    mock_post.return_value = mock_resp
    
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    # First call
    res1 = await gm.create_pull_request("token", "owner", "repo", "title", "body", "head", "base")
    assert res1["html_url"] == "http://pr"
    assert mock_post.call_count == 1
    
    # Second call should use ledger
    res2 = await gm.create_pull_request("token", "owner", "repo", "title", "body", "head", "base")
    assert res2["html_url"] == "http://pr"
    assert mock_post.call_count == 1  # No new network call
    
    wm.teardown()
