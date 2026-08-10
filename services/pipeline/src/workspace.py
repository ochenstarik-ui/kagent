import logging
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _handle_remove_readonly(func, path, exc):
    """Error handler for shutil.rmtree that removes read-only attributes."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class WorkspaceManager:
    """
    Manages an isolated git workspace for a task.
    Creates a temporary clone, a deterministic branch, and an artifacts directory
    that survives the workspace teardown.
    """

    def __init__(self, repository_url: str, task_id: str, base_branch: str = "main"):
        self.repository_url = repository_url
        self.task_id = task_id
        self.base_branch = base_branch
        self.branch_name = f"kagent/task-{task_id}"
        self.workspace_dir: Path | None = None
        self.artifacts_dir = Path.cwd() / "artifacts" / task_id

    def setup(self) -> Path:
        """Sets up the workspace and returns the path to the workspace root."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir = Path(tempfile.mkdtemp(prefix=f"kagent_ws_{self.task_id}_"))
        logger.info(f"Setting up workspace in {self.workspace_dir}")

        try:
            # Clone the repository
            subprocess.run(
                ["git", "clone", self.repository_url, str(self.workspace_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            # Create branch from current (which should be base_branch)
            subprocess.run(
                ["git", "checkout", "-b", self.branch_name],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Workspace setup failed: {e.stderr}")
            self.teardown()
            raise RuntimeError(f"Failed to set up workspace: {e.stderr}")

        return self.workspace_dir

    def teardown(self) -> None:
        """Deletes the workspace directory, but keeps the artifacts directory."""
        if self.workspace_dir and self.workspace_dir.exists():
            logger.info(f"Tearing down workspace at {self.workspace_dir}")
            shutil.rmtree(self.workspace_dir, onerror=_handle_remove_readonly)
            self.workspace_dir = None
