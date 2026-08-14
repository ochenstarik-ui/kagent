"""Account Pool — provider credential manager for KAgent reasoning-engine.

Manages multiple AI-provider accounts (opencode-go, nvidia, codex, …)
assigned to logical roles (orchestrator | subagents) with an LRU
acquire/release cycle and error-driven state transitions:

  available  → rented      (acquire)
  rented     → available   (release, success)
  rented     → throttled   (release, RateLimitError with reset_at)
  rented     → failed      (release, AuthError)
  any        → disabled    (operator: disable)
  disabled   → available   (operator: enable)
  throttled  → available   (operator: reset_throttle or auto)

Design notes
------------
- Uses asyncio.Lock per pool-role to prevent concurrent requests from
  receiving the same account (instead of DB-level SKIP LOCKED, which
  requires a real DB; this module is self-contained and testable without one).
- In ``replay`` mode (cassette playback) no account is selected at all;
  callers receive a sentinel ``REPLAY_SENTINEL`` string so cassette code can
  detect the no-op path.
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from enum import Enum
from typing import Any


REPLAY_SENTINEL = "__replay__"


class PoolState(str, Enum):
    available = "available"
    rented = "rented"
    throttled = "throttled"
    failed = "failed"
    disabled = "disabled"


class RateLimitError(Exception):
    """Raised when a provider responds with 429 / rate-limit."""

    def __init__(self, reset_at: str | None = None, default_delay: float = 60.0) -> None:
        super().__init__("rate limit exceeded")
        self.reset_at = reset_at
        self.default_delay = default_delay


class AuthError(Exception):
    """Raised when a provider responds with 401/403 (auth failure)."""


class PoolExhaustedError(Exception):
    """Raised when no accounts are available in the requested pool."""

    def __init__(self, role: str, next_available_at: float | None = None) -> None:
        msg = f"No available accounts in pool '{role}'"
        if next_available_at is not None:
            msg += f"; next available in {max(0.0, next_available_at - time.monotonic()):.0f}s"
        super().__init__(msg)
        self.role = role
        self.next_available_at = next_available_at


@dataclasses.dataclass
class Account:
    id: str
    provider: str
    pool: str
    state: PoolState = PoolState.available
    throttled_until: float | None = None  # monotonic seconds
    pinned_to_role: str | None = None     # manual pin
    last_used: float | None = None        # monotonic seconds

    def is_available(self) -> bool:
        if self.state == PoolState.available:
            return True
        if self.state == PoolState.throttled:
            if self.throttled_until is not None and time.monotonic() >= self.throttled_until:
                # Auto-clear expired throttle
                self.state = PoolState.available
                self.throttled_until = None
                return True
        return False


class AccountPool:
    """Thread-safe (via asyncio) account pool.

    Parameters
    ----------
    accounts:
        List of ``Account`` objects describing all available credentials.
    replay_mode:
        When ``True`` every ``acquire`` call immediately returns
        ``REPLAY_SENTINEL`` without touching any account state.
    """

    def __init__(self, accounts: list[Account], *, replay_mode: bool = False) -> None:
        self._accounts: list[Account] = list(accounts)
        self._replay_mode = replay_mode
        self._locks: dict[str, asyncio.Lock] = {}

    def _role_lock(self, role: str) -> asyncio.Lock:
        if role not in self._locks:
            self._locks[role] = asyncio.Lock()
        return self._locks[role]

    # ── Acquire / Release ─────────────────────────────────────────────────────

    async def acquire(self, role: str) -> str:
        """Return an account id suitable for ``role``.

        In replay mode returns ``REPLAY_SENTINEL`` without side effects.
        Raises ``PoolExhaustedError`` if no account is available.
        """
        if self._replay_mode:
            return REPLAY_SENTINEL

        async with self._role_lock(role):
            candidates = self._pool_for(role)
            available = [a for a in candidates if a.is_available()]

            if not available:
                # Find soonest throttle expiry to hint the caller
                throttled = [
                    a.throttled_until
                    for a in candidates
                    if a.state == PoolState.throttled and a.throttled_until is not None
                ]
                raise PoolExhaustedError(role, min(throttled) if throttled else None)

            # LRU: pick the one used longest ago (or never)
            chosen = min(available, key=lambda a: a.last_used or 0.0)
            chosen.state = PoolState.rented
            chosen.last_used = time.monotonic()
            return chosen.id

    async def release(
        self,
        account_id: str,
        error: Exception | None = None,
    ) -> None:
        """Return an account to the pool, applying state transitions from *error*."""
        account = self._find(account_id)
        if account is None:
            return

        if error is None:
            account.state = PoolState.available
        elif isinstance(error, RateLimitError):
            account.state = PoolState.throttled
            if error.reset_at is not None:
                # parse ISO-8601 offset if needed — keep it simple, use delay
                account.throttled_until = time.monotonic() + error.default_delay
            else:
                account.throttled_until = time.monotonic() + error.default_delay
        elif isinstance(error, AuthError):
            account.state = PoolState.failed
        else:
            # Transient / unknown — return to pool
            account.state = PoolState.available

    # ── Operator Actions ──────────────────────────────────────────────────────

    def disable(self, account_id: str) -> None:
        account = self._find(account_id)
        if account is not None:
            account.state = PoolState.disabled

    def enable(self, account_id: str) -> None:
        account = self._find(account_id)
        if account is not None:
            account.state = PoolState.available
            account.throttled_until = None

    def reset_throttle(self, account_id: str) -> None:
        account = self._find(account_id)
        if account is not None and account.state == PoolState.throttled:
            account.state = PoolState.available
            account.throttled_until = None

    def pin(self, role: str, account_id: str) -> None:
        """Bind *role* to *account_id* exclusively (manual pinning)."""
        account = self._find(account_id)
        if account is not None:
            account.pinned_to_role = role

    def unpin(self, account_id: str) -> None:
        account = self._find(account_id)
        if account is not None:
            account.pinned_to_role = None

    # ── Introspection ─────────────────────────────────────────────────────────

    def list_all(self) -> list[dict[str, Any]]:
        """Return a safe, secret-free snapshot of all accounts."""
        return [
            {
                "id": a.id,
                "provider": a.provider,
                "pool": a.pool,
                "state": a.state.value,
                "throttled_until": a.throttled_until,
                "pinned_to_role": a.pinned_to_role,
            }
            for a in self._accounts
        ]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pool_for(self, role: str) -> list[Account]:
        """Return accounts eligible for *role* (pinned-first, then pool-based)."""
        pinned = [a for a in self._accounts if a.pinned_to_role == role]
        if pinned:
            return pinned
        return [a for a in self._accounts if a.pool == role]

    def _find(self, account_id: str) -> Account | None:
        for a in self._accounts:
            if a.id == account_id:
                return a
        return None
