from fastapi import APIRouter

health_router = APIRouter(prefix="/health")


@health_router.get("", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
