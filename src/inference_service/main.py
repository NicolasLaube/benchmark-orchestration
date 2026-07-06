import time

import httpx
import typer
import uvicorn
from fastapi import FastAPI, HTTPException

from inference_service.ollama_client import OllamaClient
from inference_service.prompt import build_prompt
from inference_service.rate_limiter import ConcurrencyLimiter, RpmLimiter
from inference_service.schemas import HealthResponse, InferRequest, InferResponse


def create_app(
    model: str,
    rpm: int,
    max_concurrency: int,
    ollama_base_url: str,
    ollama_timeout_sec: float,
) -> FastAPI:
    app = FastAPI(
        title="Rate-limited Inference Service",
        description="HTTP wrapper around a local Ollama model with RPM and concurrency limits.",
        version="0.1.0",
    )

    ollama_client = OllamaClient(
        base_url=ollama_base_url,
        model=model,
        timeout_sec=ollama_timeout_sec,
    )

    rpm_limiter = RpmLimiter(rpm=rpm)
    concurrency_limiter = ConcurrencyLimiter(max_concurrency=max_concurrency)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            model=model,
            rpm_limit=rpm,
            max_concurrency=max_concurrency,
        )

    @app.post("/infer", response_model=InferResponse)
    async def infer(payload: InferRequest) -> InferResponse:
        concurrency_allowed = await concurrency_limiter.try_acquire()

        if not concurrency_allowed:
            raise HTTPException(
                status_code=429,
                headers={"Retry-After": "1"},
                detail={"error": "concurrency_limited"},
            )

        try:
            rpm_allowed, retry_after = await rpm_limiter.allow()

            if not rpm_allowed:
                raise HTTPException(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    detail={"error": "rpm_limited"},
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
) -> None:
    app = create_app(
        model=model,
        rpm=rpm,
        max_concurrency=max_concurrency,
        ollama_base_url=ollama_base_url,
        ollama_timeout_sec=ollama_timeout_sec,
    )

    uvicorn.run(app, host=host, port=port)


def app_cli() -> None:
    typer.run(run_server)


if __name__ == "__main__":
    app_cli()