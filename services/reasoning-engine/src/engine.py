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
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    success: bool = False
    error_message: Optional[str] = None
    content: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════════

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, ModelInfo] = {}
        self._provider_endpoints: dict[str, str] = {}
        self._provider_keys: dict[str, str] = {}
    
    def register(self, model: ModelInfo) -> None:
        self._models[model.id] = model
    
    def set_provider(self, name: str, endpoint: str, api_key: str) -> None:
        self._provider_endpoints[name] = endpoint
        self._provider_keys[name] = api_key
    
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
    
    def get_endpoint(self, provider: str) -> Optional[str]:
        return self._provider_endpoints.get(provider)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        return self._provider_keys.get(provider)


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
                "ts": time.time()
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
            endpoint = self.registry.get_endpoint(model.provider)
            api_key = self.registry.get_api_key(model.provider)
            
            if not endpoint:
                continue
            
            execution = ModelExecution(
                model_id=model.id,
                provider=model.provider,
            )
            
            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{endpoint}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model.model_name,
                            "messages": messages,
                            "max_tokens": min(model.max_tokens, 4096),
                        },
                    )
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
            except Exception as e:
                err_msg = str(e)
                if api_key and api_key in err_msg:
                    err_msg = err_msg.replace(api_key, "***")
                execution.error_message = err_msg
            
            execution.latency_ms = int((time.time() - start) * 1000)
            self.telemetry.append(execution)
            last_execution = execution
            
            if execution.success:
                if mode == "record":
                    with cassette_path.open("w", encoding="utf-8") as f:
                        json.dump({
                            "tokens_input": execution.tokens_input,
                            "tokens_output": execution.tokens_output,
                            "cost_usd": execution.cost_usd,
                            "latency_ms": execution.latency_ms,
                            "content": execution.content,
                        }, f, indent=2)
                return execution
        
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
    
    # Register providers (endpoints + keys from env)
    engine.registry.set_provider(
        "opencode-go",
        os.getenv("OPENCODE_GO_ENDPOINT", "http://localhost:20127"),
        os.getenv("OPENCODE_GO_API_KEY", ""),
    )
    engine.registry.set_provider(
        "xai",
        os.getenv("XAI_ENDPOINT", "http://localhost:20127"),
        os.getenv("XAI_API_KEY", ""),
    )
    engine.registry.set_provider(
        "openai",
        os.getenv("OPENAI_ENDPOINT", "http://localhost:20127"),
        os.getenv("OPENAI_API_KEY", ""),
    )
    
    # Register models
    engine.registry.register(ModelInfo(
        id="opencode-go/kimi-k2.7-code",
        provider="opencode-go",
        model_name="kimi-k2.7-code",
        capabilities=[
            Capability.CODE_GENERATION, Capability.CODE_REVIEW,
            Capability.REASONING, Capability.ANALYSIS, Capability.CHAT
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
