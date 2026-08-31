from orchestrator.domain.models.question import BenchmarkQuestion
from orchestrator.domain.scheduling.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.domain.scheduling.aimd.controller import (
    AdaptiveAimdController,
    AIMDPhase,
)
from orchestrator.domain.scheduling.common.models import AttemptOutcome


def test_controller_increases_concurrency_after_successes() -> None:
    """Verifies that the concurrency is increased after sucesses"""
    config = AdaptiveAimdSchedulerConfig(
        initial_concurrency=2,
        max_target_concurrency=10,
        successes_before_concurrency_increase=1,
    )
    controller = AdaptiveAimdController(config)

    controller.phase = AIMDPhase.ADAPTIVE

    controller.on_success()
    controller.on_success()

    assert controller.target_concurrency > 2


def test_controller_not_increased_if_success_but_not_enough_yet() -> None:
    """Verifies that the concurrency is increased after sucesses"""
    config = AdaptiveAimdSchedulerConfig(
        initial_concurrency=2,
        max_target_concurrency=10,
        successes_before_concurrency_increase=4,
    )
    controller = AdaptiveAimdController(config)

    controller.phase = AIMDPhase.ADAPTIVE

    controller.on_success()
    controller.on_success()

    assert controller.target_concurrency == 2


def test_controller_reduces_concurrency_after_concurrency_limit() -> None:
    """Verifies that the concurrency is reduced after limit reached."""
    config = AdaptiveAimdSchedulerConfig(
        initial_concurrency=8,
    )
    controller = AdaptiveAimdController(config)

    controller.on_concurrency_limited(
        AttemptOutcome(
            question=BenchmarkQuestion(
                benchmark_id=1,
                question_id=1,
                question="Fake",
                expected_answer="Fake",
            ),
            rate_limit_reason="concurrency",
            attempt=1,
        )
    )

    assert controller.target_concurrency < 8
    assert controller.target_concurrency >= 1
