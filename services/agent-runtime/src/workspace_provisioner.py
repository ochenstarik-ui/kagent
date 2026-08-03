"""Idempotent, worker-owned Git worktree provisioning."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_SAFE_BRANCH = re.compile(r"^(?!-)(?!/)(?!.*(?:\.\.|//|@\{|\\))[a-zA-Z0-9._/-]{1,200}$")
_REMOTE = re.compile(r"^(?:https|ssh|git)://", re.IGNORECASE)
_SCP_REMOTE = re.compile(r"^[\w.-]+@[\w.-]+:[\w./-]+$")


@dataclass(frozen=True)
class ProvisionedWorkspace:
    checkout_ref: str
    head_sha: str
    recovered: bool


class GitWorkspaceProvisioner:
    def __init__(
        self,
        root: Path,
        *,
        allow_local_repositories: bool = False,
        git_timeout_seconds: int = 120,
    ) -> None:
        self.root = root.resolve()
        self.allow_local_repositories = allow_local_repositories
        self.git_timeout_seconds = git_timeout_seconds
        self.mirrors = self.root / "mirrors"
        self.checkouts = self.root / "checkouts"
        self.mirrors.mkdir(parents=True, exist_ok=True)
        self.checkouts.mkdir(parents=True, exist_ok=True)

    def provision(
        self,
        workspace_id: str,
        repository_url: str,
        base_branch: str,
        branch_name: str,
    ) -> ProvisionedWorkspace:
        self._validate_identifier(workspace_id)
        self._validate_branch(base_branch)
        self._validate_branch(branch_name)
        source = self._validate_repository(repository_url)
        checkout = self._checkout_path(workspace_id)
        checkout_ref = f"checkout:{workspace_id}"

        if checkout.exists():
            head = self._verify_existing(checkout, branch_name)
            return ProvisionedWorkspace(checkout_ref, head, True)

        mirror = self._mirror_path(source)
        if not mirror.exists():
            self._git("clone", "--mirror", source, str(mirror))
        else:
            self._git("--git-dir", str(mirror), "remote", "update", "--prune")

        base_ref = f"refs/heads/{base_branch}"
        self._git("--git-dir", str(mirror), "rev-parse", "--verify", base_ref)
        branch_ref = f"refs/heads/{branch_name}"
        branch_exists = self._git(
            "--git-dir",
            str(mirror),
            "show-ref",
            "--verify",
            "--quiet",
            branch_ref,
            check=False,
        ).returncode == 0

        if branch_exists:
            self._git("--git-dir", str(mirror), "worktree", "add", str(checkout), branch_ref)
        else:
            self._git(
                "--git-dir",
                str(mirror),
                "worktree",
                "add",
                "-b",
                branch_name,
                str(checkout),
                base_ref,
            )
        head = self._verify_existing(checkout, branch_name)
        return ProvisionedWorkspace(checkout_ref, head, False)

    def cleanup(self, workspace_id: str, repository_url: str) -> bool:
        self._validate_identifier(workspace_id)
        source = self._validate_repository(repository_url)
        checkout = self._checkout_path(workspace_id)
        if not checkout.exists():
            return False
        mirror = self._mirror_path(source)
        if mirror.exists():
            self._git(
                "--git-dir",
                str(mirror),
                "worktree",
                "remove",
                "--force",
                str(checkout),
            )
            self._git("--git-dir", str(mirror), "worktree", "prune")
        elif checkout.is_relative_to(self.checkouts):
            shutil.rmtree(checkout)
        return True

    def resolve_checkout(self, checkout_ref: str) -> Path:
        if not checkout_ref.startswith("checkout:"):
            raise ValueError("Invalid checkout reference")
        workspace_id = checkout_ref.removeprefix("checkout:")
        self._validate_identifier(workspace_id)
        checkout = self._checkout_path(workspace_id)
        if not checkout.exists():
            raise FileNotFoundError("Workspace checkout does not exist")
        return checkout

    def _verify_existing(self, checkout: Path, branch_name: str) -> str:
        if not checkout.resolve().is_relative_to(self.checkouts):
            raise ValueError("Checkout escapes provisioner root")
        actual_branch = self._git(
            "-C", str(checkout), "branch", "--show-current"
        ).stdout.strip()
        if actual_branch != branch_name:
            raise ValueError("Existing checkout branch does not match task contract")
        return self._git("-C", str(checkout), "rev-parse", "HEAD").stdout.strip()

    def _checkout_path(self, workspace_id: str) -> Path:
        path = (self.checkouts / workspace_id).resolve()
        if not path.is_relative_to(self.checkouts):
            raise ValueError("Checkout escapes provisioner root")
        return path

    def _mirror_path(self, source: str) -> Path:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return (self.mirrors / f"{digest}.git").resolve()

    def _validate_repository(self, value: str) -> str:
        source = value.strip()
        if _REMOTE.match(source):
            split = urlsplit(source)
            hostname = split.hostname or ""
            if split.username or split.password:
                netloc = hostname
                if split.port:
                    netloc += f":{split.port}"
                source = urlunsplit((split.scheme, netloc, split.path, "", ""))
            return source
        if _SCP_REMOTE.match(source):
            return source
        if self.allow_local_repositories:
            local = Path(source).resolve()
            if not local.exists():
                raise ValueError("Local repository does not exist")
            return str(local)
        raise ValueError("Repository must be HTTPS, SSH, Git or SCP-style")

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError("Invalid workspace identifier")

    @staticmethod
    def _validate_branch(value: str) -> None:
        if not _SAFE_BRANCH.fullmatch(value) or value.endswith(("/", ".")):
            raise ValueError("Invalid Git branch")

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        result = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=self.git_timeout_seconds,
            env=env,
        )
        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "git command failed"
            raise RuntimeError(message[:2000])
        return result
