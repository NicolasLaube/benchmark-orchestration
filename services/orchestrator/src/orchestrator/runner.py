import logging

from orchestrator.io.benchmark import LoaderCsvBenchmark
from orchestrator.io.models import BenchmarkQuestion
from orchestrator.io.queue import LoaderJsonlQueue
from orchestrator.report.models import QuestionResult
from orchestrator.schedulers.base import Scheduler

logger = logging.getLogger(__name__)


class Runner:
    def __init__(
        self,
        loader_queue: LoaderJsonlQueue,
        loader_benchmark: LoaderCsvBenchmark,
        scheduler: Scheduler,
    ) -> None:
        self.loader_queue = loader_queue
        self.loader_benchmark = loader_benchmark
        self.scheduler = scheduler

    async def run(self, queue_path: str) -> list[QuestionResult]:
        logger.info("Loading queue from %s", queue_path)

        jobs = self.loader_queue.load(queue_path)
        logger.info("Loaded %d benchmark jobs", len(jobs))

        all_questions: list[BenchmarkQuestion] = []

        for job in jobs:
            questions = self.loader_benchmark.load(job)
            all_questions.extend(questions)

            logger.info(
                "Loaded benchmark_id=%s with %d questions from %s",
                job.id,
                len(questions),
                job.path,
            )

        logger.info("Loaded %d benchmark questions", len(all_questions))

        results = await self.scheduler.run_questions(all_questions)

        logger.info("Finished processing %d questions", len(results))

        return results
