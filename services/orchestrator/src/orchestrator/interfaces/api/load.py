import csv
import io

from fastapi import UploadFile
from orchestrator.domain.models.question import BenchmarkQuestion


async def load_questions_from_upload(
    file: UploadFile,
) -> list[BenchmarkQuestion]:
    content = await file.read()

    text = content.decode("utf-8")

    reader = csv.DictReader(io.StringIO(text))

    questions: list[BenchmarkQuestion] = []

    for index, row in enumerate(reader):
        questions.append(
            BenchmarkQuestion(
                benchmark_id=file.filename or "uploaded",
                question_id=str(index),
                question=row["question"],
                expected_answer=row["expected_answer"],
            )
        )

    return questions
