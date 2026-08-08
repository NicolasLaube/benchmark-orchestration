from inference_service.utils.prompt import build_prompt

from tests.integration.factories import make_app, request_client
from tests.integration.fakes import (
    AllowingConcurrencyLimiter,
    FailingOllamaClient,
    FakeOllamaClient,
    RejectingConcurrencyLimiter,
    RejectingRpmLimiter,
)


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


async def test_infer_rejects_invalid_payload(client) -> None:

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
