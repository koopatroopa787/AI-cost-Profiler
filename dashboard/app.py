"""FastAPI dashboard application with WebSocket support."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_cost_profiler import CostTracker, UsageRecord
from ai_cost_profiler.models import Provider
from ai_cost_profiler.pricing import PROVIDER_INFO


# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        data = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)


# Global instances
manager = ConnectionManager()
tracker: Optional[CostTracker] = None


def get_tracker() -> CostTracker:
    """Get or create the global tracker."""
    global tracker
    if tracker is None:
        tracker = CostTracker(db_path="ai_costs.db")

        def broadcast_callback(record: UsageRecord):
            asyncio.create_task(manager.broadcast({
                "type": "new_record",
                "data": {
                    "id": record.id,
                    "timestamp": record.timestamp.isoformat(),
                    "agent": record.agent,
                    "task": record.task,
                    "model": record.model,
                    "provider": record.provider.value,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "tokens": record.total_tokens,
                    "cost": round(record.total_cost, 6),
                    "latency_ms": record.latency_ms,
                }
            }))

        tracker.add_realtime_callback(broadcast_callback)

    return tracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    get_tracker()
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="AI Cost Profiler Dashboard",
        description="Real-time cost monitoring for AI agent applications",
        version="0.2.0",
        lifespan=lifespan
    )

    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    return app


app = create_app()


# ── Response models ──────────────────────────────────────────────────────────

class CostSummaryResponse(BaseModel):
    total_cost: float
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    request_count: int
    avg_cost_per_request: float
    avg_tokens_per_request: float


class AgentCostResponse(BaseModel):
    agent: str
    total_cost: float
    total_tokens: int
    request_count: int
    avg_cost_per_request: float


class TaskCostResponse(BaseModel):
    task: str
    agent: str
    total_cost: float
    total_tokens: int
    request_count: int
    avg_cost_per_request: float


class ModelCostResponse(BaseModel):
    model: str
    provider: str
    provider_name: str
    provider_icon: str
    total_cost: float
    input_cost: float
    output_cost: float
    total_tokens: int
    input_tokens: int
    output_tokens: int
    request_count: int
    avg_cost: float
    avg_latency_ms: Optional[float] = None


class ProviderCostResponse(BaseModel):
    provider: str
    provider_name: str
    provider_icon: str
    provider_url: str
    total_cost: float
    total_tokens: int
    request_count: int
    avg_cost: float
    model_count: int
    avg_latency_ms: Optional[float] = None


class ExpensivePromptResponse(BaseModel):
    prompt_hash: str
    prompt_preview: str
    avg_tokens: float
    avg_cost: float
    call_count: int
    total_cost: float
    agent: str
    task: str
    model: str
    token_ratio_vs_avg: float


class OptimizationResponse(BaseModel):
    type: str
    priority: str
    title: str
    description: str
    estimated_monthly_savings: float
    affected_agent: Optional[str] = None
    affected_task: Optional[str] = None
    current_model: Optional[str] = None
    suggested_model: Optional[str] = None


class ModelCatalogEntry(BaseModel):
    model: str
    provider: str
    input_per_1m: float
    output_per_1m: float
    context_window: int
    supports_vision: bool
    supports_tools: bool
    description: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML."""
    static_path = Path(__file__).parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse("<h1>AI Cost Profiler Dashboard</h1><p>Static files not found.</p>")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "0.2.0"}


@app.get("/api/costs/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get overall cost summary."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    summary = t.analytics.get_summary(start_time=start_time)

    return CostSummaryResponse(
        total_cost=round(summary.total_cost, 4),
        total_tokens=summary.total_tokens,
        total_input_tokens=summary.total_input_tokens,
        total_output_tokens=summary.total_output_tokens,
        request_count=summary.request_count,
        avg_cost_per_request=round(summary.avg_cost_per_request, 6),
        avg_tokens_per_request=round(summary.avg_tokens_per_request, 2)
    )


@app.get("/api/costs/by-agent", response_model=List[AgentCostResponse])
async def get_costs_by_agent(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get cost breakdown by agent."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    agents = t.analytics.get_costs_by_agent(start_time=start_time)

    return [
        AgentCostResponse(
            agent=a.agent,
            total_cost=round(a.total_cost, 4),
            total_tokens=a.total_tokens,
            request_count=a.request_count,
            avg_cost_per_request=round(a.avg_cost_per_request, 6)
        )
        for a in agents
    ]


@app.get("/api/costs/by-task", response_model=List[TaskCostResponse])
async def get_costs_by_task(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get cost breakdown by task."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    tasks = t.analytics.get_costs_by_task(start_time=start_time)

    return [
        TaskCostResponse(
            task=tk.task,
            agent=tk.agent,
            total_cost=round(tk.total_cost, 4),
            total_tokens=tk.total_tokens,
            request_count=tk.request_count,
            avg_cost_per_request=round(tk.avg_cost_per_request, 6)
        )
        for tk in tasks
    ]


@app.get("/api/costs/by-model", response_model=List[ModelCostResponse])
async def get_costs_by_model(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get cost breakdown by model."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    rows = t.analytics.get_costs_by_model(start_time=start_time)

    return [
        ModelCostResponse(
            model=r["model"],
            provider=r.get("provider", "custom"),
            provider_name=r.get("provider_name", r.get("provider", "custom")),
            provider_icon=r.get("provider_icon", "⚙️"),
            total_cost=round(r["total_cost"], 6),
            input_cost=round(r.get("input_cost", 0), 6),
            output_cost=round(r.get("output_cost", 0), 6),
            total_tokens=r.get("total_tokens", 0),
            input_tokens=r.get("input_tokens", 0),
            output_tokens=r.get("output_tokens", 0),
            request_count=r["request_count"],
            avg_cost=round(r["avg_cost"], 6),
            avg_latency_ms=round(r["avg_latency_ms"], 0) if r.get("avg_latency_ms") else None,
        )
        for r in rows
    ]


@app.get("/api/costs/by-provider", response_model=List[ProviderCostResponse])
async def get_costs_by_provider(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get cost breakdown by provider."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    rows = t.analytics.get_costs_by_provider(start_time=start_time)

    return [
        ProviderCostResponse(
            provider=r["provider"],
            provider_name=r.get("provider_name", r["provider"]),
            provider_icon=r.get("provider_icon", "⚙️"),
            provider_url=r.get("provider_url", ""),
            total_cost=round(r["total_cost"], 4),
            total_tokens=r.get("total_tokens", 0),
            request_count=r["request_count"],
            avg_cost=round(r["avg_cost"], 6),
            model_count=r.get("model_count", 1),
            avg_latency_ms=round(r["avg_latency_ms"], 0) if r.get("avg_latency_ms") else None,
        )
        for r in rows
    ]


@app.get("/api/costs/trend")
async def get_cost_trend(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get hourly cost trend for charting."""
    t = get_tracker()
    rows = t.analytics.get_hourly_trend(hours=hours)
    return rows


@app.get("/api/costs/expensive-prompts", response_model=List[ExpensivePromptResponse])
async def get_expensive_prompts(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
    limit: int = Query(10, ge=1, le=50, description="Number of prompts to return")
):
    """Get most expensive prompts."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    prompts = t.analytics.get_expensive_prompts(start_time=start_time, limit=limit)

    return [
        ExpensivePromptResponse(
            prompt_hash=p.prompt_hash,
            prompt_preview=p.prompt_preview,
            avg_tokens=round(p.avg_tokens, 2),
            avg_cost=round(p.avg_cost, 6),
            call_count=p.call_count,
            total_cost=round(p.total_cost, 4),
            agent=p.agent,
            task=p.task,
            model=p.model,
            token_ratio_vs_avg=round(p.token_ratio_vs_avg, 2)
        )
        for p in prompts
    ]


@app.get("/api/suggestions", response_model=List[OptimizationResponse])
async def get_suggestions(
    hours: int = Query(720, ge=24, le=2160, description="Hours to analyze (default 30 days)")
):
    """Get optimization suggestions."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    suggestions = t.analytics.get_optimization_suggestions(start_time=start_time)

    return [
        OptimizationResponse(
            type=s.type,
            priority=s.priority,
            title=s.title,
            description=s.description,
            estimated_monthly_savings=round(s.estimated_monthly_savings, 2),
            affected_agent=s.affected_agent,
            affected_task=s.affected_task,
            current_model=s.current_model,
            suggested_model=s.suggested_model
        )
        for s in suggestions
    ]


@app.get("/api/realtime")
async def get_realtime_stats():
    """Get real-time statistics."""
    t = get_tracker()
    return t.analytics.get_realtime_stats()


@app.get("/api/models/catalog", response_model=List[ModelCatalogEntry])
async def get_models_catalog(
    provider: Optional[str] = Query(None, description="Filter by provider key")
):
    """List all known AI models with their pricing."""
    t = get_tracker()
    models = t.pricing.list_models(provider=provider)
    return [ModelCatalogEntry(**m) for m in models]


@app.get("/api/models/providers")
async def get_providers_info():
    """List all supported providers."""
    return [
        {"key": k, **v}
        for k, v in PROVIDER_INFO.items()
    ]


@app.get("/api/costs/latency")
async def get_latency_stats(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get latency statistics."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    return t.analytics.get_latency_stats(start_time=start_time)


@app.get("/api/costs/by-user")
async def get_costs_by_user(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back")
):
    """Get cost breakdown by user."""
    t = get_tracker()
    start_time = datetime.utcnow() - timedelta(hours=hours)
    return t.analytics.get_user_costs(start_time=start_time)


# ── Record usage endpoint ────────────────────────────────────────────────────

class RecordUsageRequest(BaseModel):
    agent: str
    task: str
    model: str = "gpt-4o"
    input_tokens: int
    output_tokens: int
    provider: str = "openai"
    user: Optional[str] = None
    prompt: Optional[str] = None
    latency_ms: Optional[int] = None


@app.post("/api/record")
async def record_usage(request: RecordUsageRequest):
    """Record a usage event."""
    t = get_tracker()

    valid_providers = {p.value for p in Provider}
    provider = Provider(request.provider) if request.provider in valid_providers else Provider.CUSTOM

    record = t.record(
        agent=request.agent,
        task=request.task,
        model=request.model,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        provider=provider,
        user=request.user,
        prompt=request.prompt,
        latency_ms=request.latency_ms,
    )

    return {
        "id": record.id,
        "cost": round(record.total_cost, 6),
        "input_cost": round(record.input_cost, 6),
        "output_cost": round(record.output_cost, 6),
        "message": "Usage recorded successfully"
    }


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time cost updates."""
    await manager.connect(websocket)

    try:
        t = get_tracker()
        stats = t.analytics.get_realtime_stats()
        await websocket.send_json({"type": "initial", "data": stats})

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "refresh":
                    stats = t.analytics.get_realtime_stats()
                    await websocket.send_json({"type": "refresh", "data": stats})
            except asyncio.TimeoutError:
                await websocket.send_text("heartbeat")

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

