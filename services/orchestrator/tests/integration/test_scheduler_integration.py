import httpx
import pytest
from fastapi import FastAPI
from orchestrator.grader.substring import SubstringGrader
from orchestrator.inference_client.client import InferenceClient
from orchestrator.loaders.models import BenchmarkQuestion
from orchestrator.schedulers.fixed import (
    FixedConcurrencyScheduler,
    FixedConcurrencySchedulerConfig,
)


def create_fake_app():
    """Creates a fake inference service"""

    app = FastAPI()
    app.state.received_questions = []
    app.state.call_count = 0

    @app.post("/infer")
    async def infer(payload: dict[str, str]):
        app.state.received_questions.append(payload["question"])
        app.state.call_count += 1

        return {
            "answer": "Paris",
            "model": "fake-model",
            "latency_ms": 1,
        }

    @app.get("/health/ready")
    async def ready():
        return {
            "status": "ready",
            "model": "fake-model",
        }

    return app


@pytest.mark.anyio
async def test_inference_client():

    fake_app = create_fake_app()

    transport = httpx.ASGITransport(app=fake_app)

    async with (
        httpx.AsyncClient(transport=transport, base_url="http://test") as http_client,
        InferenceClient(endpoint="/infer", client=http_client) as client,
    ):
        result = await client.infer("Quelle est la capitale de Paris?")

    assert result.answer == "Paris"
    assert result.model == "fake-model"
    assert result.latency_ms == 1


@pytest.mark.anyio
async def test_orchestrator_runs_questions_against_inference_service():

    fake_app = create_fake_app()

    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fake_app), base_url="http://test"
        ) as http_client,
        InferenceClient(endpoint="/infer", client=http_client) as client,
    ):
        grader = SubstringGrader()
        scheduler = FixedConcurrencyScheduler(
            inference_client=client,
            config=FixedConcurrencySchedulerConfig(
                max_concurrency=2,
                max_backoff_sec=1,
                max_retries=0,
            ),
            grader=grader,
        )

        questions = [
            BenchmarkQuestion(
                benchmark_id=1,
                question_id=1,
                question="Quelle est la capitale de la France ?",
                expected_answer="Paris",
            ),
            BenchmarkQuestion(
                benchmark_id=1,
                question_id=2,
                question="Quelle est la plus grande ville de France ?",
                expected_answer="Paris",
            ),
        ]
        results = await scheduler.run_questions(questions)

    assert len(results) == 2
    assert results[0].correct
    assert results[1].correct
    assert fake_app.state.received_questions == [
        "Quelle est la capitale de la France ?",
        "Quelle est la plus grande ville de France ?",
    ]
