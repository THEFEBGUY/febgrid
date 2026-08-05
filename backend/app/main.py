import asyncio
import re
import sys
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.performance import begin_request_performance, end_request_performance, log_request_performance
from app.services.ai_job_worker import AIJobWorker


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    worker_task = None
    is_test_process = settings.environment.lower() in {"test", "testing"} or "unittest" in sys.modules
    if settings.ai_job_worker_enabled and not is_test_process:
        worker = AIJobWorker()
        worker_task = asyncio.create_task(worker.run(), name="febgrid-ai-job-worker")
        app.state.ai_job_worker = worker
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()
        if worker_task is not None:
            await worker_task

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Phase 1 backend foundation for the FebGrid Business Operating System.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Server-Timing", "X-Request-ID"],
)


@app.middleware("http")
async def request_performance_middleware(request: Request, call_next) -> Response:
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_request_id if re.fullmatch(r"[A-Za-z0-9._-]{8,128}", supplied_request_id) else str(uuid4())
    metrics, token = begin_request_performance()
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}, db;dur={metrics.db_duration_ms:.2f};desc=\"{metrics.query_count} queries\""
        return response
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        route = getattr(request.scope.get("route"), "path", "<unmatched>")
        log_request_performance(
            request_id=request_id,
            method=request.method,
            route=route,
            status_code=status_code,
            duration_ms=duration_ms,
            metrics=metrics,
        )
        end_request_performance(token)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ready", "phase": "1"}
