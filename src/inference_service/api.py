import time

import httpx
import typer
import uvicorn
from fastapi import FastAPI, HTTPException

from inference_service.ai_generator.ai_generator import AIGenerator
from inference_service.ai_generator.ollama_client import OllamaClient
from inference_service.limiters.limiter_concurrency import ConcurrencyGate, ConcurrencyLimiter
from inference_service.limiters.limiter_rpm import RpmGate, RpmLimiter
from inference_service.utils.models import HealthResponse, InferRequest, InferResponse
from inference_service.utils.prompt import build_prompt


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

    rpm_limiter: RpmGate = rpm_limiter_override or RpmLimiter(rpm=rpm)

    concurrency_limiter: ConcurrencyGate = concurrency_limiter_override or ConcurrencyLimiter(
        max_concurrency=max_concurrency
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            model=model,
        )

    @app.post("/infer", response_model=InferResponse)
    async def infer(payload: InferRequest) -> InferResponse:
        concurrency_allowed = await concurrency_limiter.try_acquire()

        if not concurrency_allowed:
            # Default retry after 1 second for concurrency limit
            # The retry on server should add a jitter there.
            raise HTTPException(
                status_code=429,
                headers={"Retry-After": "1"},
                detail=rate_limit_detail("concurrency_limited", expose_limit_reasons),
            )

        try:
            rpm_allowed, retry_after = await rpm_limiter.allow()

            if not rpm_allowed:
                raise HTTPException(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    detail=rate_limit_detail("rpm_limited", expose_limit_reasons),
                )

            prompt = build_prompt(payload.question)

            start = time.perf_counter()

            try:
                answer = await ollama_client.generate(prompt)
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "ollama_unavailable",
                        "message": str(exc),
                    },
                ) from exc

            latency_ms = int((time.perf_counter() - start) * 1000)

            return InferResponse(
                answer=answer,
                model=model,
                latency_ms=latency_ms,
            )

        finally:
            await concurrency_limiter.release()

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    model: str = "qwen2.5:0.5b",
    rpm: int = 60,
    max_concurrency: int = 4,
    ollama_base_url: str = "http://localhost:11434",
    ollama_timeout_sec: float = 120.0,
    expose_limit_reasons: bool = True,
) -> None:
    app = create_app(
        model=model,
        rpm=rpm,
        max_concurrency=max_concurrency,
        ollama_base_url=ollama_base_url,
        ollama_timeout_sec=ollama_timeout_sec,
        expose_limit_reasons=expose_limit_reasons,
    )

    # The service intentionally runs as a single Uvicorn worker because
    # rate-limit state is stored in process memory.
    uvicorn.run(app, host=host, port=port)


def rate_limit_detail(error: str, expose_limit_reasons: bool) -> dict[str, str] | str:
    if expose_limit_reasons:
        return {"error": error}

    return "rate_limited"


def app_cli() -> None:
    typer.run(run_server)


if __name__ == "__main__":
    app_cli()
