from pathlib import Path

from orchestrator.loaders.loader_queue import LoaderJsonlQueue


def test_queue_loader_reads_jsonl(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.jsonl"
    queue_file.write_text(
        '{"benchmark_id": "run_001", "csv_path": "data/benchmark.csv"}\n',
        encoding="utf-8",
    )

    jobs = LoaderJsonlQueue().load(str(queue_file))

    assert len(jobs) == 1
    assert jobs[0].id == "run_001"
    assert jobs[0].path == "data/benchmark.csv"
