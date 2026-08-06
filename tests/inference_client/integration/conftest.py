import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.inference_client.integration.factories import make_app
from tests.inference_client.integration.fakes import (
    AllowingConcurrencyLimiter,
    FakeOllamaClient,
)


@pytest.fixture
def fake_ollama() -> FakeOllamaClient:
    return FakeOllamaClient()


@pytest.fixture
def concurrency_limiter() -> AllowingConcurrencyLimiter:
    return AllowingConcurrencyLimiter()


@pytest.fixture
def app(fake_ollama, concurrency_limiter):
    return make_app(
        ollama_client=fake_ollama,
        concurrency_limiter=concurrency_limiter,
    )


@pytest_asyncio.fixture
async def client():
    app = make_app()

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
