"""KAgent Observability — metrics, logging, health aggregation.

v0.6: Prometheus-compatible metrics, structured health dashboard, alert hooks.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="KAgent Observability", version="0.6.0")

# ═══════════════════════════════════════════════════════════════════════
# Metrics store (in-memory, replace with TSDB in production)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ServiceHealth:
    name: str
    url: str
    status: str = "unknown"  # healthy, degraded, down
    last_check: Optional[str] = None
    version: Optional[str] = None

class MetricsStore:
    def __init__(self):
        self.request_count: dict[str, int] = defaultdict(int)
        self.error_count: dict[str, int] = defaultdict(int)
        self.latency_sum: dict[str, float] = defaultdict(float)
        self.latency_count: dict[str, int] = defaultdict(int)
        self.agent_executions: dict[str, int] = defaultdict(int)
        self.model_calls: dict[str, int] = defaultdict(int)
        self.pipeline_runs: dict[str, int] = defaultdict(int)
        self.alerts: list[dict[str, Any]] = []
        self.start_time = time.time()

    def record_request(self, endpoint: str, latency_ms: float, status: int):
        self.request_count[endpoint] += 1
        self.latency_sum[endpoint] += latency_ms
        self.latency_count[endpoint] += 1
        if status >= 400:
            self.error_count[endpoint] += 1

    def record_agent_execution(self, agent_id: str):
        self.agent_executions[agent_id] += 1

    def record_model_call(self, model_id: str):
        self.model_calls[model_id] += 1

    def record_pipeline_run(self, pipeline_id: str):
        self.pipeline_runs[pipeline_id] += 1

    def add_alert(self, severity: str, message: str, source: str):
        self.alerts.append({
            "severity": severity,
            "message": message,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]

    def get_metrics(self) -> dict[str, Any]:
        return {
            "uptime_seconds": int(time.time() - self.start_time),
            "requests": {
                "total": sum(self.request_count.values()),
                "by_endpoint": dict(self.request_count),
            },
            "errors": {
                "total": sum(self.error_count.values()),
                "by_endpoint": dict(self.error_count),
            },
            "latency_ms": {
                endpoint: round(self.latency_sum[endpoint] / max(self.latency_count[endpoint], 1), 1)
                for endpoint in self.latency_count
            },
            "agents": {
                "total_executions": sum(self.agent_executions.values()),
                "by_agent": dict(self.agent_executions),
            },
            "models": {
                "total_calls": sum(self.model_calls.values()),
                "by_model": dict(self.model_calls),
            },
            "pipelines": {
                "total_runs": sum(self.pipeline_runs.values()),
                "by_pipeline": dict(self.pipeline_runs),
            },
        }

    def get_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.alerts[-limit:][::-1]


store = MetricsStore()

# ═══════════════════════════════════════════════════════════════════════
# Service health aggregator
# ═══════════════════════════════════════════════════════════════════════

SERVICES = [
    ServiceHealth("gateway", "http://localhost:8080/health/live"),
    ServiceHealth("control-plane", "http://localhost:8100/health/live"),
    ServiceHealth("reasoning-engine", "http://localhost:8200/health/live"),
    ServiceHealth("agent-runtime", "http://localhost:8300/health/live"),
    ServiceHealth("pipeline", "http://localhost:8400/health/live"),
]


async def check_health(service: ServiceHealth) -> ServiceHealth:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(service.url)
            if resp.status_code == 200:
                data = resp.json()
                service.status = "healthy"
                service.version = data.get("version", "unknown")
            else:
                service.status = "degraded"
    except Exception:
        service.status = "down"
    
    service.last_check = datetime.now(timezone.utc).isoformat()
    
    if service.status == "down":
        store.add_alert("critical", f"Service {service.name} is DOWN", service.url)
    
    return service


# ═══════════════════════════════════════════════════════════════════════
# API routes
# ═══════════════════════════════════════════════════════════════════════

@app.get("/health/live")
async def health():
    return {"status": "alive", "service": "observability", "version": "0.6.0"}


@app.get("/v1/health")
async def health_dashboard():
    """Aggregate health across all KAgent services."""
    results = []
    for svc in SERVICES:
        await check_health(svc)
        results.append({
            "name": svc.name,
            "status": svc.status,
            "version": svc.version,
            "last_check": svc.last_check,
        })
    
    all_healthy = all(s.status == "healthy" for s in SERVICES)
    return {
        "overall": "healthy" if all_healthy else "degraded",
        "services": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics = store.get_metrics()
    
    prom_lines = [
        f"# HELP kagent_uptime_seconds Total uptime",
        f"# TYPE kagent_uptime_seconds gauge",
        f"kagent_uptime_seconds {metrics['uptime_seconds']}",
        f"",
        f"# HELP kagent_requests_total Total HTTP requests",
        f"# TYPE kagent_requests_total counter",
        f"kagent_requests_total {metrics['requests']['total']}",
        f"",
        f"# HELP kagent_errors_total Total HTTP errors",
        f"# TYPE kagent_errors_total counter",
        f"kagent_errors_total {metrics['errors']['total']}",
        f"",
        f"# HELP kagent_agent_executions_total Agent executions",
        f"# TYPE kagent_agent_executions_total counter",
        f"kagent_agent_executions_total {metrics['agents']['total_executions']}",
        f"",
        f"# HELP kagent_model_calls_total Model API calls",
        f"# TYPE kagent_model_calls_total counter",
        f"kagent_model_calls_total {metrics['models']['total_calls']}",
    ]
    
    return "\n".join(prom_lines) + "\n"


@app.get("/v1/alerts")
async def get_alerts(limit: int = 50):
    return {"alerts": store.get_alerts(limit)}


@app.post("/v1/metrics/record")
async def record_metric(
    metric_type: str = "request",
    endpoint: str = "unknown",
    latency_ms: float = 0,
    status: int = 200,
    agent_id: str = "",
    model_id: str = "",
    pipeline_id: str = "",
):
    if metric_type == "request":
        store.record_request(endpoint, latency_ms, status)
    elif metric_type == "agent":
        store.record_agent_execution(agent_id)
    elif metric_type == "model":
        store.record_model_call(model_id)
    elif metric_type == "pipeline":
        store.record_pipeline_run(pipeline_id)
    
    return {"status": "recorded"}


@app.get("/v1/dashboard")
async def dashboard():
    """Human-readable dashboard summary."""
    m = store.get_metrics()
    return {
        "title": "KAgent Dashboard",
        "uptime": f"{m['uptime_seconds'] // 3600}h {(m['uptime_seconds'] % 3600) // 60}m",
        "requests": m['requests']['total'],
        "errors": m['errors']['total'],
        "error_rate": f"{m['errors']['total'] / max(m['requests']['total'], 1) * 100:.1f}%",
        "agent_executions": m['agents']['total_executions'],
        "model_calls": m['models']['total_calls'],
        "pipeline_runs": m['pipelines']['total_runs'],
        "active_alerts": len(store.alerts),
        "services": [
            {"name": s.name, "url": s.url}
            for s in SERVICES
        ],
    }
