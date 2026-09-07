from typing import Protocol

from orchestrator.domain.events import QuestionCompleted


class EventProducer(Protocol):
    async def publish_question_completed(
        self,
        event: QuestionCompleted,
    ) -> None: ...
