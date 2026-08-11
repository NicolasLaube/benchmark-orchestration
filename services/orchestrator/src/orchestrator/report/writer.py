"""
This module provides functionality to save benchmark results in JSON format. It defines the
`JsonReporter` class, which is responsible for writing the benchmark summary and individual
question results to a specified output path. The results are serialized into a structured JSON
format, including metadata such as the generation timestamp, summary statistics, and detailed
results for each question.
"""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from orchestrator.report.models import BenchmarkReport


class JsonReporter:
    def write(
        self,
        output_path: str,
        report: BenchmarkReport,
    ) -> None:
        path = Path(output_path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
