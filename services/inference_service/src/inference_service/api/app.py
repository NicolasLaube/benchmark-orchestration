from fastapi import FastAPI

from inference_service.ai_generator.ai_generator import AIGenerator
from inference_service.ai_generator.ollama_client import OllamaClient
from inference_service.api.routes.health import health_router
from inference_service.api.routes.inference import inference_router
from inference_service.limiters.limiter_concurrency import (
    ConcurrencyGate,
    ConcurrencyLimiter,
)
from inference_service.limiters.limiter_rpm import RpmGate, RpmLimiter


def create_app(
    model: str,
    rpm: int,
    max_concurrency: int,
    ollama_base_url: str,
    ollama_timeout_sec: float,
    expose_limit_reasons: bool = True,
    ollama_client_override: AIGenerator | None = None,
    rpm_limiter_override: RpmGate | None = None,
    concurrency_limiter_override: ConcurrencyGate | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Rate-limited Inference Service",
        description="HTTP wrapper around a local Ollama model with RPM and concurrency limits.",
        version="0.1.0",
    )

    ollama_client: AIGenerator = ollama_client_override or OllamaClient(
        base_url=ollama_base_url,
        model=model,
        timeout_sec=ollama_timeout_sec,
    )

    app.state.ollama_client = ollama_client

    app.state.model = model

    app.state.rpm_limiter: RpmGate = rpm_limiter_override or RpmLimiter(rpm=rpm)

    app.state.concurrency_limiter: ConcurrencyGate = (
        concurrency_limiter_override
        or ConcurrencyLimiter(max_concurrency=max_concurrency)
    )

    app.state.expose_limit_reasons = expose_limit_reasons

    app.include_router(health_router)
    app.include_router(inference_router)

    return app
