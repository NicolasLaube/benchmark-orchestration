from orchestrator.events.events import QuestionCompleted


class FakeEventProducer:
    def __init__(self):
        pass

    async def publish_question_completed(
        self,
        _: QuestionCompleted,
    ) -> None:
        return
