from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Iterator


performance_logger = logging.getLogger("febgrid.performance")


@dataclass
class RequestPerformance:
    query_count: int = 0
    db_duration_ms: float = 0.0
    external_durations_ms: dict[str, float] = field(default_factory=dict)


_request_performance: ContextVar[RequestPerformance | None] = ContextVar(
    "febgrid_request_performance",
    default=None,
)


def begin_request_performance() -> tuple[RequestPerformance, Token[RequestPerformance | None]]:
    metrics = RequestPerformance()
    return metrics, _request_performance.set(metrics)


def end_request_performance(token: Token[RequestPerformance | None]) -> None:
    _request_performance.reset(token)


def record_db_duration(duration_ms: float) -> None:
    metrics = _request_performance.get()
    if metrics is None:
        return
    metrics.query_count += 1
    metrics.db_duration_ms += max(0.0, duration_ms)


def record_external_duration(service: str, duration_ms: float) -> None:
    metrics = _request_performance.get()
    if metrics is None:
        return
    safe_service = service if service in {"groq", "java_validator", "supabase_auth"} else "external"
    metrics.external_durations_ms[safe_service] = metrics.external_durations_ms.get(safe_service, 0.0) + max(0.0, duration_ms)


@contextmanager
def measure_external(service: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        record_external_duration(service, (time.perf_counter() - started) * 1000)


def log_request_performance(
    *,
    request_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
    metrics: RequestPerformance,
) -> None:
    # Deliberately exclude URLs, query strings, bodies, identities, and tokens.
    payload = {
        "event": "http_request.completed",
        "request_id": request_id,
        "method": method,
        "route": route,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "db_query_count": metrics.query_count,
        "db_duration_ms": round(metrics.db_duration_ms, 2),
        "external_durations_ms": {key: round(value, 2) for key, value in sorted(metrics.external_durations_ms.items())},
    }
    performance_logger.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))
