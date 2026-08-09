from httpx import ASGITransport, AsyncClient
from inference_service.api.app import create_app

from tests.integration.fakes import (
    AllowingConcurrencyLimiter,
    AllowingRpmLimiter,
    FakeOllamaClient,
)


def make_app(
    *,
    ollama_client=None,
    rpm_limiter=None,
    concurrency_limiter=None,
    expose_limit_reasons: bool = True,
):
    return create_app(
        model="test-model",
        rpm=60,
        max_concurrency=4,
        ollama_base_url="http://ollama:11434",
        ollama_timeout_sec=1.0,
        expose_limit_reasons=expose_limit_reasons,
        ollama_client_override=ollama_client or FakeOllamaClient(),
        rpm_limiter_override=rpm_limiter or AllowingRpmLimiter(),
        concurrency_limiter_override=(
            concurrency_limiter or AllowingConcurrencyLimiter()
        ),
    )


async def request_client(app):
    """
    Helper usable as:

        async with request_client(app) as client:
            ...
    """

    transport = ASGITransport(app=app)

    return AsyncClient(
        transport=transport,
        base_url="http://test",
    )
