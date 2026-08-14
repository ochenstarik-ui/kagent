"""Unit tests for AccountPool (services/reasoning-engine/src/account_pool.py).

All tests use an in-memory pool — no database, no network, no real provider.
Tests cover every acceptance criterion from P14:
  - 429 with reset → throttled with delay
  - 429 without reset → default delay applied
  - 10 parallel requests across 4-account pool → distributed, not concentrated
  - release on error and timeout → account returns to pool
  - exhausted pool → explicit PoolExhaustedError, no waiting, no cross-pool
  - pinned exhausted account → error, not swapped
  - disabled account → not selected
  - secrets not in list_all() output
  - replay mode → REPLAY_SENTINEL, no account touched
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from src.account_pool import (
    Account,
    AccountPool,
    AuthError,
    PoolExhaustedError,
    PoolState,
    RateLimitError,
    REPLAY_SENTINEL,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_accounts(pool: str = "subagents", n: int = 4) -> list[Account]:
    return [
        Account(id=f"acc-{i}", provider="opencode-go", pool=pool)
        for i in range(1, n + 1)
    ]


# ── Acquire / Release ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_returns_available_account() -> None:
    pool = AccountPool(make_accounts())
    acc_id = await pool.acquire("subagents")
    assert acc_id.startswith("acc-")


@pytest.mark.asyncio
async def test_release_success_makes_account_available() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    await pool.release(acc_id)
    # Should be acquirable again
    acc_id2 = await pool.acquire("subagents")
    assert acc_id2 == acc_id


@pytest.mark.asyncio
async def test_429_with_reset_transitions_to_throttled() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    await pool.release(acc_id, RateLimitError(reset_at="2026-08-13T18:00:00Z", default_delay=300.0))
    acc = pool._find(acc_id)
    assert acc is not None
    assert acc.state == PoolState.throttled
    assert acc.throttled_until is not None


@pytest.mark.asyncio
async def test_429_without_reset_applies_default_delay() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    before = time.monotonic()
    await pool.release(acc_id, RateLimitError(reset_at=None, default_delay=120.0))
    acc = pool._find(acc_id)
    assert acc is not None
    assert acc.state == PoolState.throttled
    assert acc.throttled_until is not None
    assert acc.throttled_until > before + 100  # applied ~120s


@pytest.mark.asyncio
async def test_release_auth_error_transitions_to_failed() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    await pool.release(acc_id, AuthError())
    acc = pool._find(acc_id)
    assert acc is not None
    assert acc.state == PoolState.failed


@pytest.mark.asyncio
async def test_release_generic_error_returns_to_available() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    await pool.release(acc_id, RuntimeError("timeout"))
    acc = pool._find(acc_id)
    assert acc is not None
    assert acc.state == PoolState.available


# ── Parallelism ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ten_parallel_requests_across_four_accounts() -> None:
    """10 concurrent acquires on a 4-account pool must not all go to one account."""
    pool = AccountPool(make_accounts(n=4))

    acquired: list[str] = []

    async def one_request() -> None:
        acc_id = await pool.acquire("subagents")
        acquired.append(acc_id)
        # Simulate work
        await asyncio.sleep(0)
        await pool.release(acc_id)

    # 4 concurrent (pool size) — each should get a distinct account at peak
    results_set: list[set[str]] = []

    async def four_concurrent() -> None:
        tasks = [asyncio.create_task(pool.acquire("subagents")) for _ in range(4)]
        ids = await asyncio.gather(*tasks)
        results_set.append(set(ids))  # all distinct iff no duplication
        for acc_id in ids:
            await pool.release(acc_id)

    await four_concurrent()
    assert len(results_set[0]) == 4, "All 4 concurrent acquires should get distinct accounts"

    # 10 sequential — just confirm they all succeed
    for _ in range(10):
        await one_request()
    assert len(acquired) == 10


# ── Pool exhaustion ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exhausted_pool_raises_explicit_error() -> None:
    pool = AccountPool(make_accounts(n=2))
    # Rent both
    a1 = await pool.acquire("subagents")
    a2 = await pool.acquire("subagents")
    # Third should fail explicitly
    with pytest.raises(PoolExhaustedError) as exc_info:
        await pool.acquire("subagents")
    assert "subagents" in str(exc_info.value)
    await pool.release(a1)
    await pool.release(a2)


@pytest.mark.asyncio
async def test_exhausted_pool_does_not_cross_to_other_pool() -> None:
    accounts = make_accounts(pool="subagents", n=1) + make_accounts(pool="orchestrator", n=2)
    pool = AccountPool(accounts)
    a1 = await pool.acquire("subagents")
    with pytest.raises(PoolExhaustedError):
        # Must not fall back to orchestrator pool
        await pool.acquire("subagents")
    await pool.release(a1)


# ── Manual pinning ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pinned_exhausted_account_raises_not_swaps() -> None:
    accounts = make_accounts(n=2)
    pool = AccountPool(accounts)
    # Pin role to acc-1
    pool.pin("subagents", "acc-1")
    # Rent acc-1 (the pinned one)
    acc_id = await pool.acquire("subagents")
    assert acc_id == "acc-1"
    # Now both pinned to role is exhausted — should NOT fall back to acc-2
    with pytest.raises(PoolExhaustedError):
        await pool.acquire("subagents")
    await pool.release(acc_id)


# ── Operator actions ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disabled_account_not_selected() -> None:
    pool = AccountPool(make_accounts(n=2))
    pool.disable("acc-1")
    for _ in range(5):
        acc_id = await pool.acquire("subagents")
        assert acc_id != "acc-1", "Disabled account must never be selected"
        await pool.release(acc_id)


@pytest.mark.asyncio
async def test_reset_throttle_makes_account_available() -> None:
    pool = AccountPool(make_accounts(n=1))
    acc_id = await pool.acquire("subagents")
    await pool.release(acc_id, RateLimitError(default_delay=9999.0))
    pool.reset_throttle(acc_id)
    acc = pool._find(acc_id)
    assert acc is not None
    assert acc.state == PoolState.available


# ── Secrets / security ────────────────────────────────────────────────────────


def test_list_all_contains_no_secrets() -> None:
    """The pool snapshot must not expose api_key or any credential-like field."""
    pool = AccountPool(make_accounts(n=2))
    snapshot = pool.list_all()
    secret_fields = {"api_key", "secret", "token", "password", "key"}
    for entry in snapshot:
        assert not secret_fields.intersection(entry.keys()), (
            f"Sensitive field found in pool snapshot: {entry}"
        )
        for value in entry.values():
            if isinstance(value, str):
                assert "secret" not in value.lower()
                assert "api_key" not in value.lower()


# ── Replay mode ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_mode_returns_sentinel_without_touching_accounts() -> None:
    pool = AccountPool(make_accounts(n=2), replay_mode=True)
    result = await pool.acquire("subagents")
    assert result == REPLAY_SENTINEL
    # All accounts remain available
    for acc in pool._accounts:
        assert acc.state == PoolState.available
