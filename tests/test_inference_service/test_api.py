import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from inference_service.api import create_app, rate_limit_detail
from inference_service.utils.prompt import build_prompt


class FakeOllamaClient:
    def __init__(self, answer: str = "Paris") -> None:
        self.answer = answer
        self.received_prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.received_prompts.append(prompt)
        return self.answer


class FailingOllamaClient:
    async def generate(self, prompt: str) -> str:
        request = httpx.Request(
            method="POST",
            url="http://ollama:11434/api/generate",
        )

        raise httpx.ConnectError(
            "Connection refused",
            request=request,
        )


class AllowingRpmLimiter:
    async def allow(self) -> tuple[bool, int]:
        return True, 0


class RejectingRpmLimiter:
    def __init__(self, retry_after: int = 42) -> None:
        self.retry_after = retry_after

    async def allow(self) -> tuple[bool, int]:
        return False, self.retry_after


class AllowingConcurrencyLimiter:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    async def try_acquire(self) -> bool:
        self.acquire_calls += 1
        return True

    async def release(self) -> None:
        self.release_calls += 1


class RejectingConcurrencyLimiter:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    async def try_acquire(self) -> bool:
        self.acquire_calls += 1
        return False

    async def release(self) -> None:
        self.release_calls += 1


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
        concurrency_limiter_override=(concurrency_limiter or AllowingConcurrencyLimiter()),
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


async def test_health_returns_service_information() -> None:
    app = make_app()

    client = await request_client(app)

    async with client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": "test-model",
    }


async def test_infer_returns_generated_answer() -> None:
    ollama = FakeOllamaClient(answer="The answer is Paris.")
    concurrency = AllowingConcurrencyLimiter()

    app = make_app(
        ollama_client=ollama,
        concurrency_limiter=concurrency,
    )

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={"question": "What is the capital of France?"},
        )

    assert response.status_code == 200

    body = response.json()

    assert body["answer"] == "The answer is Paris."
    assert body["model"] == "test-model"
    assert isinstance(body["latency_ms"], int)
    assert body["latency_ms"] >= 0

    assert ollama.received_prompts == [build_prompt("What is the capital of France?")]

    assert concurrency.acquire_calls == 1
    assert concurrency.release_calls == 1


async def test_infer_rejects_invalid_payload() -> None:
    app = make_app()

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={},
        )

    assert response.status_code == 422


async def test_infer_returns_429_when_rpm_limit_is_reached() -> None:
    concurrency = AllowingConcurrencyLimiter()

    app = make_app(
        rpm_limiter=RejectingRpmLimiter(retry_after=42),
        concurrency_limiter=concurrency,
    )

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={"question": "Test question"},
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    assert response.json() == {
        "detail": {
            "error": "rpm_limited",
        }
    }

    assert concurrency.acquire_calls == 1

    assert concurrency.release_calls == 1


async def test_infer_hides_rpm_limit_reason_when_disabled() -> None:
    app = make_app(
        rpm_limiter=RejectingRpmLimiter(retry_after=10),
        expose_limit_reasons=False,
    )

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={"question": "Test question"},
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "10"
    assert response.json() == {
        "detail": "rate_limited",
    }


async def test_infer_rejects_request_when_concurrency_is_full() -> None:
    concurrency = RejectingConcurrencyLimiter()

    app = make_app(
        concurrency_limiter=concurrency,
    )

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={"question": "Test question"},
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "1"
    assert response.json() == {
        "detail": {
            "error": "concurrency_limited",
        }
    }

    assert concurrency.acquire_calls == 1

    assert concurrency.release_calls == 0


async def test_infer_returns_503_when_ollama_is_unavailable() -> None:
    concurrency = AllowingConcurrencyLimiter()

    app = make_app(
        ollama_client=FailingOllamaClient(),
        concurrency_limiter=concurrency,
    )

    client = await request_client(app)

    async with client:
        response = await client.post(
            "/infer",
            json={"question": "Test question"},
        )

    assert response.status_code == 503

    body = response.json()

    assert body["detail"]["error"] == "ollama_unavailable"
    assert "Connection refused" in body["detail"]["message"]

    assert concurrency.acquire_calls == 1
    assert concurrency.release_calls == 1


@pytest.mark.parametrize(
    ("error", "expose", "expected"),
    [
        (
            "rpm_limited",
            True,
            {"error": "rpm_limited"},
        ),
        (
            "concurrency_limited",
            True,
            {"error": "concurrency_limited"},
        ),
        (
            "rpm_limited",
            False,
            "rate_limited",
        ),
        (
            "concurrency_limited",
            False,
            "rate_limited",
        ),
    ],
)
def test_rate_limit_detail(
    error: str,
    expose: bool,
    expected: dict[str, str] | str,
) -> None:
    assert rate_limit_detail(error, expose) == expected
