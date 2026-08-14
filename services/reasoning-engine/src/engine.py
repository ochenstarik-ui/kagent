import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx


# ═══════════════════════════════════════════════════════════════════════
# Domain types
# ═══════════════════════════════════════════════════════════════════════

class Capability(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    REASONING = "reasoning"
    CREATIVE = "creative"
    CHAT = "chat"


class PrivacyClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    STREAM = "stream"
    BATCH = "batch"


class TaskCategory(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    CRITICAL = "critical"


@dataclass
class ReasoningRequest:
    capability: Capability
    task_category: TaskCategory = TaskCategory.STANDARD
    context_tokens: int = 4096
    tool_requirements: list[str] = field(default_factory=list)
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    latency_target_ms: int = 30_000
    quality_target: float = 0.8
    hard_budget_usd: float = 0.50
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    role: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    id: str
    provider: str
    model_name: str
    capabilities: list[Capability]
    price_per_1k_input: float
    price_per_1k_output: float
    max_tokens: int
    avg_latency_ms: int
    quality_score: float
    privacy_support: list[PrivacyClass]
    enabled: bool = True


@dataclass
class ReasoningDecision:
    selected_model: ModelInfo
    fallback_models: list[ModelInfo]
    estimated_cost: float
    estimated_latency_ms: int
    confidence: float
    reasoning: list[str]
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ModelExecution:
    model_id: str
    provider: str
    account_id: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    success: bool = False
    error_message: Optional[str] = None
    content: Optional[str] = None



class AccountState(str, Enum):
    AVAILABLE = "available"
    THROTTLED = "throttled"
    EXHAUSTED = "exhausted"
    FAILED = "failed"
    DISABLED = "disabled"

@dataclass
class ProviderAccount:
    account_id: str
    provider: str
    endpoint: str
    api_key: str
    state: AccountState = AccountState.AVAILABLE
    reset_time: Optional[float] = None
    total_requests: int = 0
    total_cost_usd: float = 0.0
    _in_use: bool = False
    _last_used: float = 0.0

# ═══════════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════════

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, ModelInfo] = {}
        self._accounts: dict[str, ProviderAccount] = {}
        self._role_pools: dict[str, list[str]] = {}
        self._role_pinned: dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    def register(self, model: ModelInfo) -> None:
        self._models[model.id] = model
    
    def set_provider_pool(self, name: str, endpoint: str, accounts: dict[str, str]) -> None:
        for acc_id, api_key in accounts.items():
            self._accounts[acc_id] = ProviderAccount(
                account_id=acc_id,
                provider=name,
                endpoint=endpoint,
                api_key=api_key
            )
            
    def set_role_pool(self, role: str, account_ids: list[str]) -> None:
        self._role_pools[role] = account_ids

    def has_account(self, account_id: str) -> bool:
        return account_id in self._accounts
        
    def pin_account(self, role: str, account_id: str) -> None:
        self._role_pinned[role] = account_id

    def disable_account(self, account_id: str) -> None:
        if account_id in self._accounts:
            self._accounts[account_id].state = AccountState.DISABLED

    def reset_throttle(self, account_id: str) -> None:
        if account_id in self._accounts:
            acc = self._accounts[account_id]
            if acc.state == AccountState.THROTTLED:
                acc.state = AccountState.AVAILABLE
                acc.reset_time = None
    
    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)
    
    def list_capable(self, *capabilities: Capability, privacy: PrivacyClass = PrivacyClass.INTERNAL) -> list[ModelInfo]:
        return [
            m for m in self._models.values()
            if m.enabled
            and all(c in m.capabilities for c in capabilities)
            and privacy in m.privacy_support
        ]
    
    def list_all(self) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.enabled]
        
    def get_accounts_status(self) -> list[dict]:
        res = []
        for a in self._accounts.values():
            pinned_to = [r for r, aid in self._role_pinned.items() if aid == a.account_id]
            res.append({
                "account_id": a.account_id,
                "provider": a.provider,
                "state": a.state.value,
                "reset_time": a.reset_time,
                "total_requests": a.total_requests,
                "total_cost_usd": a.total_cost_usd,
                "pinned_roles": pinned_to,
            })
        return res

    async def lease_account(self, role: str, provider: str) -> ProviderAccount:
        import time
        async with self._lock:
            # 1. Clear expired throttles
            now = time.time()
            for acc in self._accounts.values():
                if acc.state == AccountState.THROTTLED and acc.reset_time and now >= acc.reset_time:
                    acc.state = AccountState.AVAILABLE
                    acc.reset_time = None

            # 2. Determine allowed accounts
            pinned_id = self._role_pinned.get(role)
            if pinned_id:
                allowed_ids = [pinned_id]
            else:
                allowed_ids = self._role_pools.get(role, [])

            candidates = [self._accounts[aid] for aid in allowed_ids if aid in self._accounts and self._accounts[aid].provider == provider]
            
            if not candidates:
                raise ValueError(f"No accounts configured for role '{role}' and provider '{provider}'")

            # Check if pinned is exhausted/in_use
            if pinned_id:
                c = candidates[0]
                if c.state != AccountState.AVAILABLE or c._in_use:
                    raise ValueError(f"Pinned account {pinned_id} is not available (state={c.state.value}, in_use={c._in_use})")
                c._in_use = True
                c._last_used = now
                return c

            # LRU choice among available
            available = [c for c in candidates if c.state == AccountState.AVAILABLE and not c._in_use]
            if not available:
                throttled = [c for c in candidates if c.state == AccountState.THROTTLED]
                if throttled:
                    next_reset = min((c.reset_time for c in throttled if c.reset_time), default=None)
                    reset_str = f" at {next_reset}" if next_reset else " (unknown reset)"
                    raise RuntimeError(f"All accounts for {provider} are throttled. Next available{reset_str}")
                else:
                    raise RuntimeError(f"Pool exhausted for {provider} and role {role}.")
            
            # Sort by least recently used
            available.sort(key=lambda x: x._last_used)
            chosen = available[0]
            chosen._in_use = True
            chosen._last_used = now
            return chosen

    async def release_account(self, account_id: str) -> None:
        async with self._lock:
            if account_id in self._accounts:
                self._accounts[account_id]._in_use = False


# ═══════════════════════════════════════════════════════════════════════
# Cost Optimizer
# ═══════════════════════════════════════════════════════════════════════

class CostOptimizer:
    def select_best(
        self,
        candidates: list[ModelInfo],
        request: ReasoningRequest,
    ) -> tuple[ModelInfo, list[ModelInfo], float]:
        """Select best model by cost-per-quality, within budget."""
        scored = []
        for model in candidates:
            # Estimated cost for this request
            est_input_cost = (request.context_tokens / 1000) * model.price_per_1k_input
            est_output_cost = (request.context_tokens / 2000) * model.price_per_1k_output  # assume 50% output
            est_total = est_input_cost + est_output_cost
            
            # Skip if over budget
            if est_total > request.hard_budget_usd:
                continue
            
            # Skip if latency too high
            if model.avg_latency_ms > request.latency_target_ms:
                continue
            
            # Score: quality / cost (efficiency)
            efficiency = model.quality_score / max(est_total, 0.0001)
            scored.append((model, est_total, efficiency))
        
        if not scored:
            raise ValueError(f"No model fits budget ${request.hard_budget_usd} for capability {request.capability.value}")
        
        # Sort by efficiency
        scored.sort(key=lambda x: x[2], reverse=True)
        
        best_model, best_cost, _ = scored[0]
        fallbacks = [s[0] for s in scored[1:4]]
        
        return best_model, fallbacks, best_cost


# ═══════════════════════════════════════════════════════════════════════
# Policy Engine (stub — will grow)
# ═══════════════════════════════════════════════════════════════════════

class PolicyEngine:
    def validate(self, request: ReasoningRequest, decision: ReasoningDecision) -> list[str]:
        violations = []
        
        # Budget check
        if decision.estimated_cost > request.hard_budget_usd * 1.1:
            violations.append(f"Cost ${decision.estimated_cost:.4f} exceeds budget ${request.hard_budget_usd:.2f}")
        
        # Privacy check
        if request.privacy_class not in decision.selected_model.privacy_support:
            violations.append(f"Model {decision.selected_model.id} does not support privacy class {request.privacy_class.value}")
        
        # Quality check
        if decision.selected_model.quality_score < request.quality_target * 0.8:
            violations.append(f"Quality {decision.selected_model.quality_score} below target {request.quality_target}")
        
        return violations


# ═══════════════════════════════════════════════════════════════════════
# Reasoning Engine Core
# ═══════════════════════════════════════════════════════════════════════

class ReasoningEngine:
    def __init__(self):
        self.registry = ModelRegistry()
        self.optimizer = CostOptimizer()
        self.policy = PolicyEngine()
        self.telemetry: list[ModelExecution] = []
    
    async def decide(self, request: ReasoningRequest) -> ReasoningDecision:
        request_id = hashlib.sha256(
            json.dumps({
                "capability": request.capability.value,
            }).encode()
        ).hexdigest()[:12]
        
        reasoning: list[str] = []
        
        # Step 1: Find capable models
        candidates = self.registry.list_capable(
            request.capability,
            privacy=request.privacy_class
        )
        reasoning.append(f"Found {len(candidates)} capable models for {request.capability.value}")
        
        if not candidates:
            raise ValueError(f"No models support capability {request.capability.value} with privacy {request.privacy_class.value}")
        
        # Step 2: Cost-optimize
        best, fallbacks, cost = self.optimizer.select_best(candidates, request)
        reasoning.append(
            f"Selected {best.id} (${cost:.4f} est, "
            f"quality={best.quality_score}, latency={best.avg_latency_ms}ms)"
        )
        
        if fallbacks:
            reasoning.append(f"Fallbacks: {', '.join(m.id for m in fallbacks)}")
        
        # Step 3: Build decision
        decision = ReasoningDecision(
            selected_model=best,
            fallback_models=fallbacks,
            estimated_cost=cost,
            estimated_latency_ms=best.avg_latency_ms,
            confidence=best.quality_score,
            reasoning=reasoning,
            request_id=request_id,
        )
        
        # Step 4: Policy check
        violations = self.policy.validate(request, decision)
        if violations:
            reasoning.append(f"WARNING: {len(violations)} policy violations: {violations}")
        
        return decision
    
    async def execute(
        self,
        decision: ReasoningDecision,
        messages: list[dict[str, str]],
        role: str = "default",
    ) -> ModelExecution:
        """Execute the actual model call."""
        import os
        import json
        import hashlib
        from pathlib import Path
        
        mode = os.environ.get("EXECUTION_MODE", "live").lower()
        cassettes_dir = Path("cassettes")
        if mode in ("record", "replay"):
            cassettes_dir.mkdir(exist_ok=True)
            
        req_hash = hashlib.sha256(json.dumps({"messages": messages}).encode()).hexdigest()[:16]
        cassette_path = cassettes_dir / f"{decision.request_id}_{req_hash}.json"
        
        if mode == "replay":
            if not cassette_path.exists():
                raise FileNotFoundError(f"Replay mode: cassette not found at {cassette_path}")
            with cassette_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            model = decision.selected_model
            execution = ModelExecution(
                model_id=model.id,
                provider=model.provider,
                account_id=data.get("account_id"),
                tokens_input=data.get("tokens_input", 0),
                tokens_output=data.get("tokens_output", 0),
                cost_usd=data.get("cost_usd", 0.0),
                latency_ms=data.get("latency_ms", 0),
                success=True,
                content=data.get("content"),
            )
            self.telemetry.append(execution)
            return execution
        
        models_to_try = [decision.selected_model] + decision.fallback_models
        last_execution = None
        
        for model in models_to_try:
            while True:  # Inner loop for retries within the same provider pool
                try:
                    account = await self.registry.lease_account(role, model.provider)
                except Exception as e:
                    # E.g. Pool exhausted or pinned account busy. Break to try next fallback model
                    if not last_execution:
                        last_execution = ModelExecution(model_id=model.id, provider=model.provider, success=False, error_message=str(e))
                    else:
                        last_execution.error_message += f" | {str(e)}"
                    break
                
                execution = ModelExecution(
                    model_id=model.id,
                    provider=model.provider,
                    account_id=account.account_id,
                )
                
                start = time.time()
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{account.endpoint}/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {account.api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model.model_name,
                                "messages": messages,
                                "max_tokens": min(model.max_tokens, 4096),
                            },
                        )
                        
                        if response.status_code == 429:
                            # Parse reset time
                            reset_str = response.headers.get("x-ratelimit-reset", response.headers.get("retry-after", "60"))
                            try:
                                reset_delay = float(reset_str)
                            except ValueError:
                                reset_delay = 60.0
                            
                            account.state = AccountState.THROTTLED
                            account.reset_time = time.time() + reset_delay
                            await self.registry.release_account(account.account_id)
                            # Retry immediately (the while loop will grab the NEXT available account)
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        
                        usage = data.get("usage", {})
                        execution.tokens_input = usage.get("prompt_tokens", 0)
                        execution.tokens_output = usage.get("completion_tokens", 0)
                        execution.cost_usd = (
                            (execution.tokens_input / 1000) * model.price_per_1k_input
                            + (execution.tokens_output / 1000) * model.price_per_1k_output
                        )
                        execution.success = True
                        choices = data.get("choices", [])
                        if choices and "message" in choices[0]:
                            execution.content = choices[0]["message"].get("content", "")
                            
                        account.total_requests += 1
                        account.total_cost_usd += execution.cost_usd
                        
                except Exception as e:
                    err_msg = str(e)
                    if account.api_key and account.api_key in err_msg:
                        err_msg = err_msg.replace(account.api_key, "***")
                    execution.error_message = err_msg
                finally:
                    await self.registry.release_account(account.account_id)
                
                execution.latency_ms = int((time.time() - start) * 1000)
                self.telemetry.append(execution)
                last_execution = execution
                
                if execution.success:
                    if mode == "record":
                        with cassette_path.open("w", encoding="utf-8") as f:
                            json.dump({
                                "account_id": execution.account_id,
                                "tokens_input": execution.tokens_input,
                                "tokens_output": execution.tokens_output,
                                "cost_usd": execution.cost_usd,
                                "latency_ms": execution.latency_ms,
                                "content": execution.content,
                            }, f, indent=2)
                    return execution
                
                # If we get here, it wasn't a 429, but it failed. Break to try next model.
                break
                
        if last_execution is None:
            return ModelExecution(
                model_id=decision.selected_model.id,
                provider=decision.selected_model.provider,
                success=False,
                error_message="No endpoints configured for any models."
            )
            
        return last_execution


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap: register known models (editable via config)
# ═══════════════════════════════════════════════════════════════════════

def create_default_engine() -> ReasoningEngine:
    engine = ReasoningEngine()
    
    # Read comma separated accounts if present, else fallback
    def parse_accounts(provider, env_var_prefix):
        accounts = {}
        for i in range(1, 10):
            key = os.getenv(f"{env_var_prefix}_{i}_API_KEY")
            if key:
                accounts[f"{provider}-{i}"] = key
        # fallback single
        if not accounts:
            single = os.getenv(f"{env_var_prefix}_API_KEY", "")
            if single:
                accounts[f"{provider}-1"] = single
        return accounts
        
    # Register providers
    provider_accounts = {
        "opencode-go": parse_accounts("oc", "OPENCODE_GO"),
        "xai": parse_accounts("xai", "XAI"),
        "openai": parse_accounts("oai", "OPENAI"),
    }
    engine.registry.set_provider_pool(
        "opencode-go",
        os.getenv("OPENCODE_GO_ENDPOINT", "http://localhost:20127"),
        provider_accounts["opencode-go"],
    )
    engine.registry.set_provider_pool(
        "xai",
        os.getenv("XAI_ENDPOINT", "https://api.x.ai/v1"),
        provider_accounts["xai"],
    )
    engine.registry.set_provider_pool(
        "openai",
        os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1"),
        provider_accounts["openai"],
    )
    
    # Configure roles
    all_account_ids = [
        account_id
        for accounts in provider_accounts.values()
        for account_id in accounts
    ]
    for role in ["default", "orchestrator", "subagents"]:
        pools = os.getenv(f"POOL_{role.upper()}")
        account_ids = (
            [account_id.strip() for account_id in pools.split(",") if account_id.strip()]
            if pools
            else all_account_ids
        )
        engine.registry.set_role_pool(role, account_ids)
    
    # Register models
    engine.registry.register(ModelInfo(
        id="opencode-go/kimi-k2.7-code",
        provider="opencode-go",
        model_name="kimi-k2.7-code",
        capabilities=[
            Capability.CODE_GENERATION, Capability.CODE_REVIEW,
            Capability.REASONING, Capability.ANALYSIS, Capability.CHAT, Capability.PLANNING
        ],
        price_per_1k_input=0.0015,
        price_per_1k_output=0.006,
        max_tokens=131072,
        avg_latency_ms=8000,
        quality_score=0.85,
        privacy_support=[PrivacyClass.PUBLIC, PrivacyClass.INTERNAL],
    ))
    
    engine.registry.register(ModelInfo(
        id="xai/grok-4",
        provider="xai",
        model_name="grok-4",
        capabilities=[
            Capability.CODE_GENERATION, Capability.CODE_REVIEW,
            Capability.REASONING, Capability.ANALYSIS, Capability.CREATIVE,
            Capability.PLANNING, Capability.CHAT
        ],
        price_per_1k_input=0.005,
        price_per_1k_output=0.015,
        max_tokens=131072,
        avg_latency_ms=5000,
        quality_score=0.90,
        privacy_support=[PrivacyClass.PUBLIC],
    ))
    
    engine.registry.register(ModelInfo(
        id="opencode-go/deepseek-v4-pro",
        provider="opencode-go",
        model_name="deepseek-v4-pro",
        capabilities=[
            Capability.CODE_GENERATION, Capability.RESEARCH,
            Capability.ANALYSIS, Capability.REASONING,
        ],
        price_per_1k_input=0.005,
        price_per_1k_output=0.002,
        max_tokens=65536,
        avg_latency_ms=12000,
        quality_score=0.82,
        privacy_support=[PrivacyClass.PUBLIC, PrivacyClass.INTERNAL],
    ))
    
    return engine
