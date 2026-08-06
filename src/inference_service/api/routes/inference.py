import time

import httpx
from fastapi import APIRouter, HTTPException, Request

from inference_service.utils.models import (
    InferRequest,
    InferResponse,
)
from inference_service.utils.prompt import build_prompt

inference_router = APIRouter(tags=["infer"])


def rate_limit_detail(error: str, expose_limit_reasons: bool) -> dict[str, str] | str:
    if expose_limit_reasons:
        return {"error": error}

    return "rate_limited"


@inference_router.post("/infer", response_model=InferResponse)
async def infer(payload: InferRequest, request: Request) -> InferResponse:
    concurrency_limiter = request.app.state.concurrency_limiter
    rpm_limiter = request.app.state.rpm_limiter
    ollama_client = request.app.state.ollama_client
    expose_limit_reasons = request.app.state.expose_limit_reasons
    model = request.app.state.model

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
