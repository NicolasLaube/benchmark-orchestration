from pathlib import Path

from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.loaders.loader_models import BenchmarkJob


def test_benchmark_loader_reads_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "benchmark.csv"
    csv_file.write_text(
        "id,question,expected_answer\n1,What is the capital of France?,Paris\n",
        encoding="utf-8",
    )

    job = BenchmarkJob(
        id="run_001",
        path=str(csv_file),
    )

    questions = LoaderCsvBenchmark().load(job)

    assert len(questions) == 1
    assert questions[0].benchmark_id == "run_001"
    assert questions[0].question_id == "1"
    assert questions[0].question == "What is the capital of France?"
    assert questions[0].expected_answer == "Paris"
