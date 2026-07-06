import csv
from pathlib import Path

from orchestrator.models import BenchmarkJob, BenchmarkQuestion


class LoaderCsvBenchmark:
    REQUIRED_COLUMNS = {"id", "question", "expected_answer"}

    def load(self, job: BenchmarkJob) -> list[BenchmarkQuestion]:
        csv_path = Path("data", job.path)

        if not csv_path.exists():
            raise FileNotFoundError(f"BenchmarkJob CSV not found: {csv_path}")

        questions: list[BenchmarkQuestion] = []

        with csv_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(f"BenchmarkJob CSV is empty or invalid: {csv_path}")

            missing_columns = self.REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    f"BenchmarkJob CSV {csv_path} is missing required columns: "
                    f"{sorted(missing_columns)}"
                )

            for row_number, row in enumerate(reader, start=2):
                question_id = row.get("id", "").strip()
                question = row.get("question", "").strip()
                expected_answer = row.get("expected_answer", "").strip()

                if not question_id:
                    raise ValueError(
                        f"Missing id in benchmarkJobBenchmarkJob CSV {csv_path} at row {row_number}"
                    )

                if not question:
                    raise ValueError(
                        f"Missing question in benchmarkJobBenchmarkJob CSV {csv_path} at row {row_number}"
                    )

                if not expected_answer:
                    raise ValueError(
                        f"Missing expected_answer in benchmarkJobBenchmarkJob CSV {csv_path} at row {row_number}"
                    )

                questions.append(
                    BenchmarkQuestion(
                        benchmark_id=job.id,
                        question_id=question_id,
                        question=question,
                        expected_answer=expected_answer,
                    )
                )

        if not questions:
            raise ValueError(f"BenchmarkJob CSV contains no questions: {csv_path}")

        return questions