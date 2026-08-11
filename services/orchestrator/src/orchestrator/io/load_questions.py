import logging

from orchestrator.io.benchmark import LoaderCsvBenchmark
from orchestrator.io.models import BenchmarkQuestion
from orchestrator.io.queue import LoaderJsonlQueue

logger = logging.getLogger(__name__)


def load_questions(
    queue_path: str,
) -> list[BenchmarkQuestion]:
    queue_loader = LoaderJsonlQueue()
    benchmark_loader = LoaderCsvBenchmark()

    logger.info(
        "Loading queue from %s",
        queue_path,
    )

    jobs = queue_loader.load(queue_path)

    logger.info(
        "Loaded %d benchmark jobs",
        len(jobs),
    )

    questions: list[BenchmarkQuestion] = []

    for job in jobs:
        benchmark_questions = benchmark_loader.load(job)

        questions.extend(benchmark_questions)

        logger.info(
            "Loaded benchmark_id=%s with %d questions from %s",
            job.id,
            len(benchmark_questions),
            job.path,
        )

    return questions
