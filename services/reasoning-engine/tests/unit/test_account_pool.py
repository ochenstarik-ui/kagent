import asyncio
import time
import pytest
from httpx import Response
from src.engine import (
    ModelRegistry,
    ProviderAccount,
    AccountState,
    ReasoningEngine,
    ModelInfo,
    Capability,
    PrivacyClass,
    ReasoningDecision
)

@pytest.fixture
def engine():
    engine = ReasoningEngine()
    engine.registry.set_provider_pool(
        "test-provider",
        "http://mock",
        {"acc-1": "key-1", "acc-2": "key-2", "acc-3": "key-3"}
    )
    engine.registry.set_role_pool("default", ["acc-1", "acc-2", "acc-3"])
    engine.registry.set_role_pool("admin", ["acc-1"])
    
    engine.registry.register(ModelInfo(
        id="test-provider/model-1",
        provider="test-provider",
        model_name="model-1",
        capabilities=[Capability.CHAT],
        price_per_1k_input=0.01,
        price_per_1k_output=0.01,
        max_tokens=1000,
        avg_latency_ms=100,
        quality_score=0.9,
        privacy_support=[PrivacyClass.INTERNAL],
    ))
    return engine

@pytest.mark.asyncio
async def test_lease_account_round_robin(engine):
    a1 = await engine.registry.lease_account("default", "test-provider")
    assert a1.account_id in ["acc-1", "acc-2", "acc-3"]
    
    a2 = await engine.registry.lease_account("default", "test-provider")
    assert a2.account_id != a1.account_id
    
    a3 = await engine.registry.lease_account("default", "test-provider")
    assert a3.account_id != a2.account_id and a3.account_id != a1.account_id

    # release one
    await engine.registry.release_account(a2.account_id)
    a4 = await engine.registry.lease_account("default", "test-provider")
    assert a4.account_id == a2.account_id

@pytest.mark.asyncio
async def test_exhausted_pool(engine):
    a1 = await engine.registry.lease_account("default", "test-provider")
    a2 = await engine.registry.lease_account("default", "test-provider")
    a3 = await engine.registry.lease_account("default", "test-provider")
    
    with pytest.raises(RuntimeError) as e:
        await engine.registry.lease_account("default", "test-provider")
    assert "Pool exhausted" in str(e.value)

@pytest.mark.asyncio
async def test_throttle_reset(engine):
    a1 = await engine.registry.lease_account("default", "test-provider")
    a1.state = AccountState.THROTTLED
    a1.reset_time = time.time() + 0.1
    await engine.registry.release_account(a1.account_id)
    
    # Try to lease all
    a2 = await engine.registry.lease_account("default", "test-provider")
    a3 = await engine.registry.lease_account("default", "test-provider")
    
    with pytest.raises(RuntimeError) as e:
        await engine.registry.lease_account("default", "test-provider")
    assert "All accounts for test-provider are throttled" in str(e.value)
    
    await asyncio.sleep(0.2)
    # Throttle should expire
    a4 = await engine.registry.lease_account("default", "test-provider")
    assert a4.account_id == a1.account_id

@pytest.mark.asyncio
async def test_pinned_account(engine):
    engine.registry.pin_account("admin", "acc-3")
    a1 = await engine.registry.lease_account("admin", "test-provider")
    assert a1.account_id == "acc-3"
    
    with pytest.raises(ValueError) as e:
        await engine.registry.lease_account("admin", "test-provider")
    assert "is not available" in str(e.value)

@pytest.mark.asyncio
async def test_secrets_dont_leak(engine):
    status = engine.registry.get_accounts_status()
    for s in status:
        assert "api_key" not in s
        assert "key-" not in str(s)
