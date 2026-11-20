"""FastAPI entry point. Run: uvicorn app.main:app --reload"""

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .benchmark import run_benchmark
from .config import ROOT, Settings
from .harness import AgentHarness
from .providers import Provider, make_provider
from .schemas import BenchmarkRequest, BenchmarkSummary, RunRequest, RunResult
from .storage import RunStore
from .tools import Tools


def create_app(settings: Settings | None = None, provider: Provider | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = RunStore(settings.database_path)
    harness = AgentHarness(
        provider or make_provider(settings), Tools(settings.notes_path), store,
        settings.provider, settings.model,
    )
    api = FastAPI(title="Self-Improving AI Agent Harness", version="1.0.0",
                  description="Plan -> execute tools -> evaluate -> retry. Demo mode works offline.")
    api.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @api.get("/", include_in_schema=False)
    def home():
        return FileResponse(ROOT / "static" / "index.html")

    @api.get("/health")
    def health():
        return {"status": "ok", "provider": settings.provider,
                "model": harness.model, "ground_truth_required_for_factual_scoring": True}

    @api.post("/agent/run", response_model=RunResult)
    def execute_task(request: RunRequest):
        return harness.run(request)

    @api.post("/benchmark/run", response_model=BenchmarkSummary)
    def benchmark(request: BenchmarkRequest):
        try:
            return run_benchmark(harness, settings.benchmark_path, request.limit, request.max_attempts)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/runs")
    def list_runs(limit: int = Query(default=15, ge=1, le=100)):
        return store.recent(limit)

    @api.get("/runs/{run_id}", response_model=RunResult)
    def get_run(run_id: str):
        result = store.get(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return result

    return api


app = create_app()
