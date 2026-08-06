import httpx
from fastapi import APIRouter, HTTPException, Request

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "up"}


@health_router.get("/ready")
async def readiness(request: Request) -> dict[str, str]:
    ollama_client = request.app.ollama_client
    try:
        model_available = await ollama_client.health_check()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": "ollama_unavailable",
                "message": str(exc),
            },
        ) from exc

    if not model_available:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": "model_unavailable",
                "model": request.app.state.model,
            },
        )

    return {
        "status": "ready",
        "model": request.app.state.model,
    }
