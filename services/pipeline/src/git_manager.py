"""Git workspace manager — single workspace, path-filtered indexing, idempotent effects.

v0.1: GitManager + TaskContract + EffectLedger for the pipeline service.
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Task Contract
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TaskContract:
    """Declarative execution boundaries for a task."""

    id: str
    project_id: str
    objective: str
    repository: str = ""
    base_branch: str = "main"
    base_sha: str = ""

    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)

    allowed_actions: list[str] = field(default_factory=lambda: [
        "read_repository", "edit_files", "run_tests",
        "create_branch", "create_commit",
    ])
    approval_required: list[str] = field(default_factory=list)

    max_minutes: int = 120
    max_model_cost: float = 20.0
    max_changed_files: int = 30
    max_agent_turns: int = 80
    max_repair_cycles: int = 3


class ContractViolation(Exception):
    """Raised when an action would violate the task contract."""


def check_path_allowed(
    path: str,
    allowed: list[str],
    forbidden: list[str],
) -> bool:
    """Return True only if *path* is permitted by the contract rules.

    Rules:
    1. If *forbidden* matches, always reject.
    2. If *allowed* is non-empty, accept only prefixes that match.
    3. If *allowed* is empty, accept everything not forbidden.
    """
    normalised = path.replace("\\", "/").strip("/")

    for fp in forbidden:
        fp_norm = fp.replace("\\", "/").strip("/")
        if normalised == fp_norm or normalised.startswith(fp_norm + "/"):
            return False

    if not allowed:
        return True

    for ap in allowed:
        ap_norm = ap.replace("\\", "/").strip("/")
        if normalised == ap_norm or normalised.startswith(ap_norm + "/"):
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════
# Effect Ledger — in-memory for unit tests, PostgreSQL in production
# ═══════════════════════════════════════════════════════════════════════

class EffectState(str, Enum):
    INTENDED = "intended"
    IN_FLIGHT = "in_flight"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class EffectRecord:
    idempotency_key: str
    effect_type: str
    target_system: str
    request_digest: str
    state: EffectState = EffectState.INTENDED
    external_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EffectLedger:
    """Append-only effect ledger (in-memory implementation for tests)."""

    def __init__(self) -> None:
        self._records: dict[str, EffectRecord] = {}

    def lookup(self, key: str) -> Optional[EffectRecord]:
        return self._records.get(key)

    def record_intended(
        self,
        key: str,
        effect_type: str,
        target_system: str,
        request_digest: str,
    ) -> EffectRecord:
        """Write an 'intended' record. If the key already exists, return it."""
        existing = self._records.get(key)
        if existing is not None:
            return existing
        rec = EffectRecord(
            idempotency_key=key,
            effect_type=effect_type,
            target_system=target_system,
            request_digest=request_digest,
        )
        self._records[key] = rec
        return rec

    def transition(self, key: str, state: EffectState, external_id: Optional[str] = None) -> None:
        rec = self._records.get(key)
        if rec is None:
            raise KeyError(f"Effect not found: {key}")
        rec.state = state
        rec.updated_at = datetime.now(timezone.utc).isoformat()
        if external_id is not None:
            rec.external_id = external_id


# ═══════════════════════════════════════════════════════════════════════
# GitManager
# ═══════════════════════════════════════════════════════════════════════

def _idempotency_key(run_id: str, effect_type: str, digest: str) -> str:
    return hashlib.sha256(f"{run_id}:{effect_type}:{digest}".encode()).hexdigest()


def _payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


class GitManager:
    """Workspace-aware Git operations with path filtering and idempotency.

    Owns a single workspace directory shared with the AgentRuntime context.
    Teardown occurs only in `finally` after commit/push/PR or a confirmed error.
    """

    def __init__(
        self,
        workspace: Path,
        contract: TaskContract,
        ledger: Optional[EffectLedger] = None,
        run_id: str = "",
    ) -> None:
        self.workspace = workspace.resolve()
        self.contract = contract
        self.ledger = ledger or EffectLedger()
        self.run_id = run_id or contract.id

    # ── Low-level Git helpers ────────────────────────────────────────

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=check,
        )

    def _head_sha(self) -> str:
        return self._git("rev-parse", "HEAD").stdout.strip()

    # ── Workspace / ref verification ─────────────────────────────────

    def verify_base_sha(self) -> None:
        """Fetch latest refs and verify that the contract's base_sha is ancestor of HEAD."""
        self._git("fetch", "origin", self.contract.base_branch, check=False)
        if self.contract.base_sha:
            result = self._git(
                "merge-base", "--is-ancestor",
                self.contract.base_sha, "HEAD",
                check=False,
            )
            if result.returncode != 0:
                raise ContractViolation(
                    f"Base SHA {self.contract.base_sha} is not an ancestor of HEAD"
                )

    # ── Path filtering ───────────────────────────────────────────────

    def filter_paths(self, paths: list[str]) -> list[str]:
        """Return only paths that pass the contract's allowed/forbidden rules."""
        return [
            p for p in paths
            if check_path_allowed(p, self.contract.allowed_paths, self.contract.forbidden_paths)
        ]

    def _get_changed_files(self) -> list[str]:
        """List files changed relative to HEAD (unstaged + staged + untracked)."""
        # Unstaged and staged
        result = self._git("diff", "--name-only", "HEAD", check=False)
        files = [f for f in result.stdout.strip().splitlines() if f]

        # Untracked
        untracked = self._git("ls-files", "--others", "--exclude-standard")
        files.extend(f for f in untracked.stdout.strip().splitlines() if f)

        return list(set(files))

    # ── Contract limits check ────────────────────────────────────────

    def check_limits(self, elapsed_minutes: float = 0, model_cost: float = 0,
                     agent_turns: int = 0, repair_cycles: int = 0) -> None:
        """Raise ContractViolation if any limit is exceeded."""
        changed = self._get_changed_files()
        allowed_changed = self.filter_paths(changed)

        if len(allowed_changed) > self.contract.max_changed_files:
            raise ContractViolation(
                f"Changed files ({len(allowed_changed)}) exceeds max ({self.contract.max_changed_files})"
            )
        if elapsed_minutes > self.contract.max_minutes:
            raise ContractViolation(
                f"Elapsed time ({elapsed_minutes}m) exceeds max ({self.contract.max_minutes}m)"
            )
        if model_cost > self.contract.max_model_cost:
            raise ContractViolation(
                f"Model cost (${model_cost}) exceeds max (${self.contract.max_model_cost})"
            )
        if agent_turns > self.contract.max_agent_turns:
            raise ContractViolation(
                f"Agent turns ({agent_turns}) exceeds max ({self.contract.max_agent_turns})"
            )
        if repair_cycles > self.contract.max_repair_cycles:
            raise ContractViolation(
                f"Repair cycles ({repair_cycles}) exceeds max ({self.contract.max_repair_cycles})"
            )

    # ── Idempotent Git operations ────────────────────────────────────

    def create_branch(self, branch_name: str) -> str:
        """Idempotent branch creation. Returns the SHA at which the branch points."""
        payload = {"branch": branch_name}
        key = _idempotency_key(self.run_id, "create_branch", _payload_digest(payload))

        existing = self.ledger.lookup(key)
        if existing and existing.state == EffectState.SUCCEEDED:
            return existing.external_id or self._head_sha()

        self.ledger.record_intended(key, "create_branch", "git", _payload_digest(payload))
        self.ledger.transition(key, EffectState.IN_FLIGHT)

        try:
            # Check if branch already exists
            check = self._git("rev-parse", "--verify", branch_name, check=False)
            if check.returncode == 0:
                sha = check.stdout.strip()
                self._git("checkout", branch_name)
            else:
                self._git("checkout", "-b", branch_name)
                sha = self._head_sha()

            self.ledger.transition(key, EffectState.SUCCEEDED, external_id=sha)
            return sha
        except Exception as e:
            self.ledger.transition(key, EffectState.FAILED)
            raise

    def create_commit(self, message: str) -> Optional[str]:
        """Idempotent commit. Indexes only allowed paths, skips forbidden.

        Returns the commit SHA or None if nothing to commit.
        """
        # Idempotency key derived from message only — on replay the file list
        # will be empty (already committed), but the key stays stable.
        payload = {"message": message}
        key = _idempotency_key(self.run_id, "create_commit", _payload_digest(payload))

        existing = self.ledger.lookup(key)
        if existing and existing.state == EffectState.SUCCEEDED:
            return existing.external_id

        # Gather changed files and filter
        all_changed = self._get_changed_files()
        allowed = self.filter_paths(all_changed)
        forbidden = [p for p in all_changed if p not in allowed]

        if forbidden:
            logger.warning("Skipping forbidden paths from index: %s", forbidden)

        if not allowed:
            logger.info("No allowed changes to commit")
            return None

        # Check file count limit
        if len(allowed) > self.contract.max_changed_files:
            raise ContractViolation(
                f"Changed files ({len(allowed)}) exceeds max ({self.contract.max_changed_files})"
            )


        self.ledger.record_intended(key, "create_commit", "git", _payload_digest(payload))
        self.ledger.transition(key, EffectState.IN_FLIGHT)

        try:
            # Reset index, then add only allowed paths
            self._git("reset", "HEAD", check=False)
            for path in allowed:
                self._git("add", "--", path)

            # Append task identifier trailer
            full_message = f"{message}\n\nTask: {self.contract.id}\nRun: {self.run_id}"

            result = self._git("commit", "-m", full_message, check=False)
            if result.returncode != 0:
                if "nothing to commit" in result.stdout + result.stderr:
                    self.ledger.transition(key, EffectState.SUCCEEDED, external_id=None)
                    return None
                raise RuntimeError(f"git commit failed: {result.stderr}")

            sha = self._head_sha()
            self.ledger.transition(key, EffectState.SUCCEEDED, external_id=sha)
            return sha
        except ContractViolation:
            self.ledger.transition(key, EffectState.FAILED)
            raise
        except Exception:
            self.ledger.transition(key, EffectState.FAILED)
            raise

    def push(self, branch_name: str, remote: str = "origin") -> str:
        """Idempotent push. No force-push."""
        payload = {"branch": branch_name, "remote": remote}
        key = _idempotency_key(self.run_id, "push", _payload_digest(payload))

        existing = self.ledger.lookup(key)
        if existing and existing.state == EffectState.SUCCEEDED:
            return existing.external_id or ""

        self.ledger.record_intended(key, "push", "git", _payload_digest(payload))
        self.ledger.transition(key, EffectState.IN_FLIGHT)

        try:
            result = self._git("push", remote, branch_name, check=False)
            if result.returncode != 0:
                # Already up to date is ok
                if "Everything up-to-date" in result.stderr:
                    sha = self._head_sha()
                    self.ledger.transition(key, EffectState.SUCCEEDED, external_id=sha)
                    return sha
                raise RuntimeError(f"git push failed: {result.stderr}")

            sha = self._head_sha()
            self.ledger.transition(key, EffectState.SUCCEEDED, external_id=sha)
            return sha
        except Exception:
            self.ledger.transition(key, EffectState.FAILED)
            raise
