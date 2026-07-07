import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from orchestrator.models import QuestionResult


class JsonReporter:
    def write(
        self,
        output_path: str,
        summary: dict,
        results: list[QuestionResult],
    ) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
            "results": [asdict(result) for result in results],
        }

        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
