import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx
from .ledger import EffectLedger

logger = logging.getLogger(__name__)


class GitManager:
    """Manages git operations like commits, pushes, and PR creation within a workspace."""

    def __init__(self, workspace_dir: Path, ledger: EffectLedger):
        self.workspace_dir = workspace_dir
        self.ledger = ledger

    def verify_paths(self, allowed_paths: list[str]) -> bool:
        """
        Verifies that all modified files (staged and unstaged) match allowed paths.
        An empty allowed_paths means no restrictions.
        """
        if not allowed_paths:
            return True

        try:
            # Check untracked and modified files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--modified", "--exclude-standard"],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            changed_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

            for file in changed_files:
                allowed = any(file.startswith(allowed) or file == allowed for allowed in allowed_paths)
                if not allowed:
                    logger.error(f"Path verification failed: {file} is not in allowed_paths")
                    return False
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify paths: {e.stderr}")
            return False

    def commit_changes(self, task_id: str, run_id: str, message: str) -> None:
        """Adds all changes and commits them with Task-ID and Run-ID trailers."""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], cwd=self.workspace_dir, check=True)

            # Check if there are changes to commit
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            if not status.stdout.strip():
                logger.info("No changes to commit.")
                return

            # Append trailers
            full_message = f"{message}\n\nTask-ID: {task_id}\nRun-ID: {run_id}"
            
            # Note: We configure user.name and user.email locally to avoid errors if not set
            subprocess.run(["git", "config", "user.name", "KAgent"], cwd=self.workspace_dir, check=True)
            subprocess.run(["git", "config", "user.email", "kagent@example.com"], cwd=self.workspace_dir, check=True)

            subprocess.run(
                ["git", "commit", "-m", full_message],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Changes committed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Commit failed: {e.stderr}")
            raise RuntimeError(f"Commit failed: {e.stderr}")

    def push_branch(self, branch_name: str) -> None:
        """Pushes the branch. Refuses to force push."""
        try:
            subprocess.run(
                ["git", "push", "origin", branch_name],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Branch {branch_name} pushed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Push failed: {e.stderr}")
            raise RuntimeError(f"Push failed: {e.stderr}")

    async def create_pull_request(
        self,
        token: str,
        repo_owner: str,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """
        Creates a PR on GitHub using the provided token.
        Idempotent: records the effect in the ledger.
        """
        effect_key = f"pr_create_{head}_{base}"
        existing = self.ledger.get_effect(effect_key)
        if existing:
            logger.info(f"PR already created, returning cached result for {effect_key}")
            return existing

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            self.ledger.record_effect(effect_key, result)
            return result
