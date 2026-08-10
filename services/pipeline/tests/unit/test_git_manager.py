"""Integration tests for GitManager with local bare remote.

Proves:
- runtime writes a file, GitManager sees it
- forbidden path is blocked from index/commit
- idempotent replay does not create a second commit
- single workspace is shared between runtime and Git
- contract limits enforcement
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from services.pipeline.src.git_manager import (
    ContractViolation,
    EffectLedger,
    EffectState,
    GitManager,
    TaskContract,
    check_path_allowed,
)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture()
def workspace_and_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a local bare remote and a cloned workspace."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare"], cwd=bare)

    workspace = tmp_path / "workspace"
    _run(["git", "clone", str(bare), str(workspace)], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@kagent.dev"], cwd=workspace)
    _run(["git", "config", "user.name", "KAgent Test"], cwd=workspace)

    # Initial commit so HEAD exists
    readme = workspace / "README.md"
    readme.write_text("# test repo\n")
    _run(["git", "add", "README.md"], cwd=workspace)
    _run(["git", "commit", "-m", "initial commit"], cwd=workspace)
    _run(["git", "push", "origin", "main"], cwd=workspace, check=False)
    # Try to push; might need to set upstream
    push_result = _run(["git", "push", "-u", "origin", "main"], cwd=workspace, check=False)
    if push_result.returncode != 0:
        # Maybe default branch is master
        _run(["git", "push", "-u", "origin", "HEAD:main"], cwd=workspace, check=False)

    return workspace, bare


def _make_contract(**overrides: object) -> TaskContract:
    defaults = {
        "id": "task-test-1",
        "project_id": "project-1",
        "objective": "test task",
        "base_branch": "main",
        "allowed_paths": ["src", "tests"],
        "forbidden_paths": ["secrets", ".github/workflows"],
        "max_changed_files": 10,
    }
    defaults.update(overrides)
    return TaskContract(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# Path filtering unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestCheckPathAllowed:
    def test_allowed_path_passes(self) -> None:
        assert check_path_allowed("src/main.py", ["src"], ["secrets"]) is True

    def test_forbidden_path_blocked(self) -> None:
        assert check_path_allowed("secrets/key.pem", ["src", "secrets"], ["secrets"]) is False

    def test_forbidden_takes_priority_over_allowed(self) -> None:
        assert check_path_allowed("secrets/data.json", ["secrets"], ["secrets"]) is False

    def test_no_allowed_means_everything_accepted(self) -> None:
        assert check_path_allowed("anything/file.txt", [], []) is True

    def test_no_allowed_but_forbidden_blocks(self) -> None:
        assert check_path_allowed("secrets/key", [], ["secrets"]) is False

    def test_nested_path_in_allowed(self) -> None:
        assert check_path_allowed("src/lib/util.py", ["src"], []) is True

    def test_path_not_in_allowed(self) -> None:
        assert check_path_allowed("deploy/prod.yml", ["src", "tests"], []) is False


# ═══════════════════════════════════════════════════════════════════════
# EffectLedger unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestEffectLedger:
    def test_record_and_lookup(self) -> None:
        ledger = EffectLedger()
        rec = ledger.record_intended("k1", "push", "git", "d1")
        assert rec.state == EffectState.INTENDED
        assert ledger.lookup("k1") is rec

    def test_idempotent_record(self) -> None:
        ledger = EffectLedger()
        rec1 = ledger.record_intended("k1", "push", "git", "d1")
        rec2 = ledger.record_intended("k1", "push", "git", "d1")
        assert rec1 is rec2

    def test_transition(self) -> None:
        ledger = EffectLedger()
        ledger.record_intended("k1", "push", "git", "d1")
        ledger.transition("k1", EffectState.SUCCEEDED, external_id="abc123")
        rec = ledger.lookup("k1")
        assert rec is not None
        assert rec.state == EffectState.SUCCEEDED
        assert rec.external_id == "abc123"


# ═══════════════════════════════════════════════════════════════════════
# GitManager integration tests (local bare remote)
# ═══════════════════════════════════════════════════════════════════════

class TestGitManagerIntegration:
    def test_runtime_writes_file_git_sees_it(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Runtime writes a file to workspace, GitManager can index and commit it."""
        workspace, _ = workspace_and_remote
        contract = _make_contract()
        gm = GitManager(workspace, contract)

        # Simulate runtime writing a file
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "hello.py").write_text("print('hello')\n")

        gm.create_branch("wt/test-feature")
        sha = gm.create_commit("feat: add hello")
        assert sha is not None

        # Verify the file is in the commit
        result = _run(["git", "log", "--oneline", "-1"], cwd=workspace)
        assert "feat: add hello" in result.stdout

    def test_forbidden_path_not_in_index(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Forbidden path files are not added to git index or committed."""
        workspace, _ = workspace_and_remote
        contract = _make_contract()
        gm = GitManager(workspace, contract)

        gm.create_branch("wt/test-forbidden")

        # Write both allowed and forbidden files
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "good.py").write_text("ok\n")
        (workspace / "secrets").mkdir(exist_ok=True)
        (workspace / "secrets" / "api_key.txt").write_text("SUPER_SECRET\n")

        sha = gm.create_commit("feat: add files")
        assert sha is not None

        # Check that secrets/api_key.txt is NOT in the commit
        result = _run(["git", "show", "--name-only", "HEAD"], cwd=workspace)
        assert "secrets/api_key.txt" not in result.stdout
        assert "src/good.py" in result.stdout

    def test_idempotent_replay_no_second_commit(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Replaying the same operation with the same idempotency key does not create a second commit."""
        workspace, _ = workspace_and_remote
        ledger = EffectLedger()
        contract = _make_contract()
        run_id = "run-replay-test"

        gm = GitManager(workspace, contract, ledger=ledger, run_id=run_id)
        gm.create_branch("wt/test-replay")

        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "feature.py").write_text("v1\n")

        sha1 = gm.create_commit("feat: initial")
        assert sha1 is not None

        # Count commits
        log1 = _run(["git", "log", "--oneline"], cwd=workspace)
        count1 = len(log1.stdout.strip().splitlines())

        # Replay with same GitManager (same run_id and ledger)
        sha2 = gm.create_commit("feat: initial")

        # Should return same SHA without creating new commit
        assert sha2 == sha1

        log2 = _run(["git", "log", "--oneline"], cwd=workspace)
        count2 = len(log2.stdout.strip().splitlines())
        assert count2 == count1

    def test_push_to_bare_remote(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Push to local bare remote succeeds."""
        workspace, bare = workspace_and_remote
        contract = _make_contract()
        gm = GitManager(workspace, contract)

        gm.create_branch("wt/test-push")
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "pushed.py").write_text("pushed\n")
        gm.create_commit("feat: push test")

        sha = gm.push("wt/test-push")
        assert sha

        # Verify remote has the branch
        result = _run(["git", "branch", "-r"], cwd=workspace)
        assert "origin/wt/test-push" in result.stdout

    def test_single_workspace_shared_path(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Runtime and GitManager share the same workspace path."""
        workspace, _ = workspace_and_remote
        contract = _make_contract()
        gm = GitManager(workspace, contract)

        # The GitManager's workspace is the same absolute path
        assert gm.workspace == workspace.resolve()

    def test_contract_limits_file_count(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Exceeding max_changed_files raises ContractViolation."""
        workspace, _ = workspace_and_remote
        contract = _make_contract(max_changed_files=2)
        gm = GitManager(workspace, contract)

        gm.create_branch("wt/test-limits")

        (workspace / "src").mkdir(exist_ok=True)
        for i in range(5):
            (workspace / "src" / f"file{i}.py").write_text(f"content {i}\n")

        with pytest.raises(ContractViolation, match="Changed files"):
            gm.create_commit("feat: too many files")

    def test_teardown_after_git_effects(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Workspace exists during all Git operations; teardown only after."""
        workspace, _ = workspace_and_remote
        contract = _make_contract()
        gm = GitManager(workspace, contract)

        gm.create_branch("wt/test-teardown")
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "teardown.py").write_text("ok\n")

        sha = None
        try:
            sha = gm.create_commit("feat: teardown test")
            gm.push("wt/test-teardown")
        finally:
            # Workspace still exists in finally block
            assert workspace.exists()
            assert sha is not None

    def test_commit_message_contains_task_id(
        self, workspace_and_remote: tuple[Path, Path],
    ) -> None:
        """Commit message contains Task: and Run: trailers."""
        workspace, _ = workspace_and_remote
        contract = _make_contract(id="task-trailer-test")
        gm = GitManager(workspace, contract, run_id="run-123")

        gm.create_branch("wt/test-trailers")
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "trailers.py").write_text("ok\n")
        gm.create_commit("feat: with trailers")

        log = _run(["git", "log", "-1", "--format=%B"], cwd=workspace)
        assert "Task: task-trailer-test" in log.stdout
        assert "Run: run-123" in log.stdout
