from orchestrator.domain.events import QuestionCompleted


class InMemoryEventProducer:
    def __init__(self):
        self.results: list[QuestionCompleted] = []

    async def publish_question_completed(
        self,
        event: QuestionCompleted,
    ) -> None:
        self.results.append(event)
