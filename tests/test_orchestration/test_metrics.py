# tests/test_metrics.py

from orchestrator.report.report_metrics_collector import MetricsCollector
from orchestrator.report.report_models import QuestionResult


def test_metrics_collector_summarizes_results() -> None:
    results = [
        QuestionResult(
            benchmark_id="run_001",
            question_id="1",
            question="Q1",
            expected_answer="Paris",
            answer="Paris",
            correct=True,
            score=1.0,
            latency_ms=100,
            attempts=1,
            status="success",
        ),
        QuestionResult(
            benchmark_id="run_001",
            question_id="2",
            question="Q2",
            expected_answer="96",
            answer=None,
            correct=False,
            score=0.0,
            latency_ms=None,
            attempts=1,
            status="failed",
            error="boom",
        ),
    ]

    summary = MetricsCollector().summarize(
        results=results,
        total_wall_time_sec=2.0,
    )

    assert summary["total_requests"] == 2
    assert summary["successful_requests"] == 1
    assert summary["failure_count"] == 1
    assert summary["accuracy"] == 1.0
    assert summary["throughput_req_s"] == 1.0
