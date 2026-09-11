from fastapi import APIRouter, HTTPException
from orchestrator.infrastructure.messaging.redis.client import redis_client
from orchestrator.infrastructure.persistence.db import SessionLocal
from sqlalchemy import text

health_router = APIRouter(prefix="/health")


@health_router.get("/health/ready")
async def health_ready():
    checks = {}

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        checks["postgres"] = "down"

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "down"

    if "down" in checks.values():
        raise HTTPException(
            status_code=503,
            detail=checks,
        )

    return {
        "status": "ready",
        "checks": checks,
    }
