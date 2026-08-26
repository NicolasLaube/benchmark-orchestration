class EventProducer:
    def __init__(self, redis):
        self.redis = redis

    async def question_completed(
        self,
        run_id,
        question_id,
        success,
        latency_ms,
    ):
        self.redis.xadd(
            "benchmark-events",
            {
                "type": "question_completed",
                "run_id": str(run_id),
                "question_id": str(question_id),
                "success": str(success),
                "latency_ms": str(latency_ms),
            },
        )
