import httpx
import pytest
from fastapi import FastAPI, Response
from orchestrator.grader.substring import SubstringGrader
from orchestrator.inference_client.client import InferenceClient
from orchestrator.io.models import BenchmarkQuestion
from orchestrator.schedulers.fixed import (
    FixedConcurrencyScheduler,
    FixedConcurrencySchedulerConfig,
)


def create_rate_limited_fake_app():
    app = FastAPI()
    app.state.call_count = 0

    @app.post("/infer")
    async def infer(payload: dict[str, str]):
        app.state.call_count += 1

        if app.state.call_count == 1:
            return Response(
                status_code=429,
                headers={"Retry-After": "1"},
                content='{"detail":{"error":"rpm_limited"}}',
                media_type="application/json",
            )

        return {
            "answer": "Paris",
            "model": "fake-model",
            "latency_ms": 1,
        }

    return app


@pytest.mark.anyio
async def test_scheduler_retries_after_rate_limit():
    fake_app = create_rate_limited_fake_app()

    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fake_app),
            base_url="http://test",
        ) as http_client,
        InferenceClient(
            endpoint="/infer",
            client=http_client,
        ) as client,
    ):
        scheduler = FixedConcurrencyScheduler(
            inference_client=client,
            grader=SubstringGrader(),
            config=FixedConcurrencySchedulerConfig(
                max_concurrency=1,
                max_retries=1,
                max_backoff_sec=1,
            ),
        )

        questions = [
            BenchmarkQuestion(
                benchmark_id=1,
                question_id=1,
                question="Quelle est la capitale de la France ?",
                expected_answer="Paris",
            ),
        ]

        results = await scheduler.run_questions(questions)

    assert len(results) == 1
    assert results[0].correct
    assert fake_app.state.call_count == 2
