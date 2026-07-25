"""Reasoning Engine API Server — capability-first model routing."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Optional

from .engine import (
    ReasoningEngine,
    ReasoningRequest,
    Capability,
    PrivacyClass,
    ExecutionMode,
    TaskCategory,
    create_default_engine,
)

app = FastAPI(
    title="KAgent Reasoning Engine",
    version="0.1.0",
    description="Capability-first model router with budget-aware optimization",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_default_engine()


# ═══════════════════════════════════════════════════
# Request/Response models
# ═══════════════════════════════════════════════════

class DecideRequest(BaseModel):
    capability: str
    task_category: str = "standard"
    context_tokens: int = 4096
    tool_requirements: list[str] = Field(default_factory=list)
    privacy_class: str = "internal"
    latency_target_ms: int = 30000
    quality_target: float = 0.8
    hard_budget_usd: float = 0.50
    execution_mode: str = "sync"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResult(BaseModel):
    model_id: str
    provider: str
    model_name: str
    estimated_cost: float
    estimated_latency_ms: int
    quality_score: float


class DecideResponse(BaseModel):
    request_id: str
    selected: ModelResult
    fallbacks: list[ModelResult]
    estimated_cost: float
    confidence: float
    reasoning: list[str]


class ExecuteRequest(BaseModel):
    request_id: str
    messages: list[dict[str, str]]


class ExecuteResponse(BaseModel):
    success: bool
    model_id: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    error: Optional[str] = None


class ModelInfoResponse(BaseModel):
    id: str
    provider: str
    model_name: str
    capabilities: list[str]
    price_per_1k_input: float
    price_per_1k_output: float
    quality_score: float
    enabled: bool


# ═══════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════

@app.get("/health/live")
async def health_live():
    return {"status": "alive", "service": "reasoning-engine", "version": "0.1.0"}


@app.get("/health/ready")
async def health_ready():
    models = len(engine.registry.list_all())
    return {
        "status": "ready",
        "models_registered": models,
        "telemetry_entries": len(engine.telemetry),
    }


@app.get("/v1/models", response_model=list[ModelInfoResponse])
async def list_models():
    return [
        ModelInfoResponse(
            id=m.id,
            provider=m.provider,
            model_name=m.model_name,
            capabilities=[c.value for c in m.capabilities],
            price_per_1k_input=m.price_per_1k_input,
            price_per_1k_output=m.price_per_1k_output,
            quality_score=m.quality_score,
            enabled=m.enabled,
        )
        for m in engine.registry.list_all()
    ]


@app.post("/v1/decide", response_model=DecideResponse)
async def decide_model(request: DecideRequest):
    try:
        internal = ReasoningRequest(
            capability=Capability(request.capability),
            task_category=TaskCategory(request.task_category),
            context_tokens=request.context_tokens,
            tool_requirements=request.tool_requirements,
            privacy_class=PrivacyClass(request.privacy_class),
            latency_target_ms=request.latency_target_ms,
            quality_target=request.quality_target,
            hard_budget_usd=request.hard_budget_usd,
            execution_mode=ExecutionMode(request.execution_mode),
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    decision = await engine.decide(internal)
    
    return DecideResponse(
        request_id=decision.request_id,
        selected=ModelResult(
            model_id=decision.selected_model.id,
            provider=decision.selected_model.provider,
            model_name=decision.selected_model.model_name,
            estimated_cost=decision.estimated_cost,
            estimated_latency_ms=decision.estimated_latency_ms,
            quality_score=decision.selected_model.quality_score,
        ),
        fallbacks=[
            ModelResult(
                model_id=m.id,
                provider=m.provider,
                model_name=m.model_name,
                estimated_cost=0.0,  # computed on use
                estimated_latency_ms=m.avg_latency_ms,
                quality_score=m.quality_score,
            )
            for m in decision.fallback_models
        ],
        estimated_cost=decision.estimated_cost,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
    )


@app.post("/v1/execute", response_model=ExecuteResponse)
async def execute_model(request: ExecuteRequest):
    # Simulated execute — in real impl, look up the prior decision
    execution = engine.telemetry[-1] if engine.telemetry else None
    
    return ExecuteResponse(
        success=execution.success if execution else False,
        model_id=execution.model_id if execution else "unknown",
        tokens_input=execution.tokens_input if execution else 0,
        tokens_output=execution.tokens_output if execution else 0,
        cost_usd=execution.cost_usd if execution else 0.0,
        latency_ms=execution.latency_ms if execution else 0,
        error=execution.error_message if execution else "No execution found",
    )


@app.get("/v1/telemetry")
async def get_telemetry():
    return {
        "total_calls": len(engine.telemetry),
        "total_cost_usd": sum(e.cost_usd for e in engine.telemetry),
        "success_rate": sum(1 for e in engine.telemetry if e.success) / max(len(engine.telemetry), 1),
        "recent": [
            {
                "model": e.model_id,
                "cost": round(e.cost_usd, 4),
                "latency_ms": e.latency_ms,
                "success": e.success,
            }
            for e in engine.telemetry[-10:]
        ],
    }
