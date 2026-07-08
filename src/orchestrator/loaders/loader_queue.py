import json
from pathlib import Path

from orchestrator.models import BenchmarkJob


class LoaderJsonlQueue:
    def load(self, path: str) -> list[BenchmarkJob]:
        queue_path = Path(path)

        if not queue_path.exists():
            raise FileNotFoundError(f"Queue file not found: {queue_path}")

        jobs: list[BenchmarkJob] = []

        with queue_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in queue file {queue_path} at line {line_number}"
                    ) from exc

                try:
                    benchmark_id = raw["benchmark_id"]
                    csv_path = raw["csv_path"]
                except KeyError as exc:
                    raise ValueError(
                        f"Missing required field {exc} in queue file "
                        f"{queue_path} at line {line_number}"
                    ) from exc

                if not isinstance(benchmark_id, str) or not benchmark_id.strip():
                    raise ValueError(
                        f"Invalid benchmark_id in queue file {queue_path} at line {line_number}"
                    )

                if not isinstance(csv_path, str) or not csv_path.strip():
                    raise ValueError(
                        f"Invalid csv_path in queue file {queue_path} at line {line_number}"
                    )

                jobs.append(
                    BenchmarkJob(
                        id=benchmark_id.strip(),
                        path=csv_path.strip(),
                    )
                )

        if not jobs:
            raise ValueError(f"Queue file is empty: {queue_path}")

        return jobs
